import time
from typing import List, Any, Dict
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import FIDBaseRule
from app.fid.models import CheckResult
from app.fid.utils.parse_block_attributes import parse_block_attributes
import pandas as pd
import json

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)


class BlockAttributeCheck(FIDBaseRule):
    rule_type = "warning"
    rule_name = '图块属性修改'

    DEFAULT_FIELDS = ["VMB_TYPE", 'I/O']
    # io\

    ATTRIBUTIONS = {
        'TAKEOFF': ['CS', 'CT', 'FLOW_UNIT', 'DESIGN_FLOW'],
        'VMB_CHEMICAL': ["CT.", "CS.", "ID.", "DESIGN_FLOW", 'FLOW_UNIT'],
        'VMB_GASNAME': ["CT.", "CS.", "ID.", "DESIGN_FLOW", 'FLOW_UNIT'],
        'I_LINE': ["ID."],
        'GPB': ["ID.", "CS."],
        'NEW_INTER_': ["CS"],
    }

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device=None, request_data=None) -> List[CheckResult]:
        global_start = time.time()
        print(f"[block_attribute_modified] Start checking device: {device}")

        if device is not None:
            equipments = equipments.get(device, [])

        if len(equipments) == 0:
            return []

        results = []

        # --- 1. 数据准备与预处理 (关键优化点) ---
        df_prep_start = time.time()

        interface_pd = pd.DataFrame.from_dict(request_data['interface_list']).add_prefix('INTERFACE.')
        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')

        if interface_pd.empty:
            interface_pd = pd.DataFrame([], columns=['id', 'field_id', 'uni_code', 'cad_block_id']).add_prefix(
                'INTERFACE.')
        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id', 'code', 'uni_code', 'cad_block_id',
                                                 'insert_point_x', 'insert_point_y', 'insert_point_z']).add_prefix(
                'FIELD.')

        final_df = pd.merge(
            field_pd,
            interface_pd,
            left_on='FIELD.id',
            right_on='INTERFACE.field_id',
            how='left'
        )

        # 【优化核心】：将 DataFrame 转换为字典，Key 为 uni_code
        # 这样查找的时间复杂度从 O(N) 降为 O(1)
        # 注意：如果有重复的 uni_code，这里只保留最后一个（通常业务逻辑中 uni_code 应唯一，或者取第一个均可，视具体需求而定）
        # 使用 to_dict('records') 然后构建字典，或者直接利用 set_index
        # 【优化核心】：将 DataFrame 转换为字典，Key 为 uni_code
        # 这样查找的时间复杂度从 O(N) 降为 O(1)

        if not final_df.empty:
            # --- 修复开始 ---
            # 1. 检查是否有重复的 uni_code
            duplicate_count = final_df['INTERFACE.uni_code'].duplicated().sum()
            if duplicate_count > 0:
                print(
                    f"[WARNING] 发现 {duplicate_count} 条重复的 INTERFACE.uni_code 记录，正在执行去重策略（保留最后一条）...")
                # 2. 去重：基于 'INTERFACE.uni_code' 列，保留最后一条记录 (keep='last')
                # 如果业务要求保留第一条，请将 keep='last' 改为 keep='first'
                final_df_dedup = final_df.drop_duplicates(subset=['INTERFACE.uni_code'], keep='last')
            else:
                final_df_dedup = final_df

            try:
                # 3. 设置索引并转换字典
                # 此时索引保证唯一，不会再抛出 ValueError
                lookup_dict = final_df_dedup.set_index('INTERFACE.uni_code').to_dict(orient='index')
            except ValueError as e:
                # 极端兜底：如果去重后仍然失败（理论上不可能），打印错误并初始化为空字典，避免程序崩溃
                print(f"[ERROR] 构建查找字典失败：{e}。跳过该步骤，后续查找将全部失效。")
                lookup_dict = {}
            # --- 修复结束 ---

            print(f"[INFO] 字典大小：{len(lookup_dict)} 条记录 (原始行数：{len(final_df)})")
        else:
            lookup_dict = {}
            print(f"[INFO] 数据为空，字典大小为 0")

        df_prep_end = time.time()
        print(f"[PERF] DataFrame 准备与字典构建耗时：{(df_prep_end - df_prep_start) * 1000:.2f} ms")
        print(f"[INFO] 字典大小：{len(lookup_dict)} 条记录")

        # 确定描述
        if device == 'TAKEOFF':
            description = "ID_Short 不变前提下，和上一版数据相比图块属性修改："
        elif device.startswith('VMB'):
            description = 'ID 不变前提下，和上一版数据相比图块属性修改：'
        else:
            description = 'ID_Short 不变前提下，和上一版数据相比图块属性修改：'

        def log_time(step_name, start_ts):
            end_ts = time.time()
            duration_ms = (end_ts - start_ts) * 1000
            # 只有当耗时超过 1ms 才打印，避免日志过多，或者你可以保留全部
            if duration_ms > 0.5:
                print(f"  [TIME] {step_name}: {duration_ms:.2f} ms")
            return end_ts

        # --- 2. 主循环 ---
        loop_start = time.time()

        for idx, eq in enumerate(equipments):
            step_start = time.time()

            # 解析属性
            parse_start = time.time()
            try:
                equipments_info = parse_block_attributes(eq, request_data['filename'])
            except Exception as e:
                print(f"[ERROR] parse_block_attributes failed for eq {idx}: {e}")
                equipments_info = []
            # log_time(f"Eq[{idx}] parse_block_attributes", parse_start)

            for info_idx, info in enumerate(equipments_info):
                inner_step_start = time.time()
                modify_cache = []
                desc_changes = []  # 【新增】用于收集 description 中的字段变化详情
                interface_detail = ''
                field_detail = ''

                # 【优化核心】：字典查找替代 DataFrame 筛选
                filter_start = time.time()
                uni_code = info.get('interface_code')

                # 直接从字典获取，耗时接近 0
                target_dict = lookup_dict.get(uni_code)

                filter_end = log_time(f"  -> Eq[{idx}]-Info[{info_idx}] Dict Lookup", filter_start)

                compare_start = time.time()
                if target_dict is not None:
                    # target_dict 现在直接就是一个字典，不需要 iloc[0].to_dict()

                    # 提取变量 (保持原有逻辑)
                    cs = target_dict.get('INTERFACE.con_size', '')
                    ct = target_dict.get('INTERFACE.con_type', '')
                    flow_unit = target_dict.get('INTERFACE.unit', '')
                    design_flow = target_dict.get('INTERFACE.max_design_flow', '')
                    vmb_type = target_dict.get('FIELD.vmb_type', '')

                    # NaN 处理 (字典取值可能直接是 np.nan，需要转换)
                    import math
                    def clean_val(val):
                        if val is None: return ''
                        if isinstance(val, float) and math.isnan(val): return ''
                        return str(val)

                    cs = clean_val(cs)
                    ct = clean_val(ct)
                    flow_unit = clean_val(flow_unit)
                    design_flow = clean_val(design_flow)
                    vmb_type = clean_val(vmb_type)

                    # --- 比对逻辑 ---
                    if device == 'TAKEOFF':
                        if (cs or info['connection_size']) and cs != info['connection_size']:
                            modify_cache.append('cs')
                            desc_changes.append(f"cs({cs},{str(info['connection_size'])})")  # 【修改】
                            interface_detail += f"CS 修改 ({cs}) -> ({info['connection_size']})\n"
                        if (ct or info['connection_type']) and ct != info['connection_type']:
                            modify_cache.append('ct')
                            desc_changes.append(f"ct({ct},{str(info['connection_type'])})")  # 【修改】
                            interface_detail += f"CT 修改 ({ct}) -> ({info['connection_type']})\n"
                        if (flow_unit or info['flow_unit']) and flow_unit != info['flow_unit']:
                            modify_cache.append('flow_unit')
                            desc_changes.append(f"flow_unit({flow_unit},{str(info['flow_unit'])})")  # 【修改】
                            interface_detail += f"flow_unit 修改 ({flow_unit}) -> ({info['flow_unit']})\n"
                        if (design_flow or info['design_flow']) and design_flow != info['design_flow']:
                            modify_cache.append('design_flow')
                            desc_changes.append(f"design_flow({design_flow},{str(info['design_flow'])})")  # 【修改】
                            interface_detail += f"design_flow 修改 ({design_flow}) -> ({info['design_flow']})\n"

                    elif device in ['VMB_CHEMICAL', 'VMB_GASNAME']:
                        if (cs or info['connection_size']) and cs != info['connection_size']:
                            modify_cache.append('cs')
                            desc_changes.append(f"cs({cs},{str(info['connection_size'])})")  # 【修改】
                            interface_detail += f"CS 修改 ({cs}) -> ({info['connection_size']})\n"
                        if (ct or info['connection_type']) and ct != info['connection_type']:
                            modify_cache.append('ct')
                            desc_changes.append(f"ct({ct},{str(info['connection_type'])})")  # 【修改】
                            interface_detail += f"CT 修改 ({ct}) -> ({info['connection_type']})\n"
                        if (flow_unit or info['flow_unit']) and flow_unit != info['flow_unit']:
                            modify_cache.append('flow_unit')
                            desc_changes.append(f"flow_unit({flow_unit},{str(info['flow_unit'])})")  # 【修改】
                            interface_detail += f"flow_unit 修改 ({flow_unit}) -> ({info['flow_unit']})\n"
                        if (design_flow or info['design_flow']) and design_flow != info['design_flow']:
                            modify_cache.append('design_flow')
                            desc_changes.append(f"design_flow({design_flow},{str(info['design_flow'])})")  # 【修改】
                            interface_detail += f"design_flow 修改 ({design_flow}) -> ({info['design_flow']})\n"
                        if (vmb_type or info['vmb-type']) and vmb_type != info['vmb-type']:
                            modify_cache.append('vmb-type')
                            desc_changes.append(f"vmb-type({vmb_type},{str(info['vmb-type'])})")  # 【修改】
                            field_detail += f"vmb_type 修改 ({vmb_type}) -> ({info['vmb-type']})\n"

                    elif device in ['I_LINE', 'GPB']:
                        if (cs or info['connection_size']) and cs != info['connection_size']:
                            modify_cache.append('cs')
                            desc_changes.append(f"cs({cs},{str(info['connection_size'])})")  # 【修改】
                            interface_detail += f"CS 修改 ({cs}) -> ({info['connection_size']})\n"

                    elif device == 'NEW_INTER_':
                        if (cs or info['connection_size']) and cs != info['connection_size']:
                            modify_cache.append('cs')
                            desc_changes.append(f"cs({cs},{str(info['connection_size'])})")  # 【修改】
                            interface_detail += f"CS 修改 ({cs}) -> ({info['connection_size']})\n"

                log_time(f"  -> Eq[{idx}]-Info[{info_idx}] Attribute Compare", compare_start)

                # 特殊规则
                # if request_data.get('fab', {}).get('name', '').endswith(('1', '2', '3')) and device not in ['TAKEOFF',
                #                                                                                             'VMB_CHEMICAL',
                #                                                                                             'VMB_GASNAME'] and 'cs' in modify_cache:
                #     modify_cache.remove('cs')
                if request_data.get('fab', {}).get('name', '').endswith(request_data['disable_fab']) and 'ES' in \
                        request_data['filename'] and 'cs' in modify_cache:
                    modify_cache.remove('cs')
                    desc_changes = [d for d in desc_changes if not d.startswith('cs')]  # 【新增】同步移除

                # 结果追加
                if len(modify_cache) > 0:
                    append_start = time.time()
                    if 'vmb-type' in modify_cache or 'I/O' in modify_cache:
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="图块属性修改",
                            description=description + ' '.join(desc_changes),  # 【修改】使用详细变化列表
                            detail=description + field_detail,
                            equipment=[eq],
                            operation=f'update',
                            field_or_interface='field',
                            device=device
                        ))
                    else:
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="图块属性修改",
                            description=description + ','.join(desc_changes),  # 【修改】使用详细变化列表
                            detail=description + interface_detail,
                            equipment=[eq, info],
                            operation=f'update',
                            field_or_interface='interface',
                            device=device
                        ))
                    # log_time(f"  -> Eq[{idx}]-Info[{info_idx}] Append Result", append_start)

                # log_time(f"  -> Eq[{idx}]-Info[{info_idx}] Total Inner Loop", inner_step_start)

            # log_time(f"Eq[{idx}] Total Outer Loop", step_start)

        loop_end = time.time()
        print(f"[PERF] 主循环总耗时：{(loop_end - loop_start) * 1000:.2f} ms")
        print(f"[PERF] 整个 check 函数总耗时：{(time.time() - global_start) * 1000:.2f} ms")
        print(f"[RESULT] 发现警告数量：{len(results)}")

        return results


if __name__ == '__main__':
    pass
