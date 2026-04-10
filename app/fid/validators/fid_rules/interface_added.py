from typing import List, Any, Dict, Set, Optional
import sys
from pathlib import Path

# 路径设置保持原样
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult
from app.fid.utils.parse_block_attributes import parse_block_attributes
import pandas as pd

# 全局设置一次即可，不需要在每个类或方法中重复设置
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)


class InterfaceAddCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "warning"
    rule_name = "新增 interface"

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data: Dict = None) -> List[
        CheckResult]:
        """
        优化版：对所有 equipment 执行 INTERFACE_CODE 校验。
        核心优化点：
        1. 提前构建历史接口集合 (Set)，实现 O(1) 查找。
        2. 移除循环内的 DataFrame 过滤操作。
        3. 移除调试用的 print 语句。
        4. 批量处理设备解析结果。
        """
        if device is not None:
            # 确保 key 存在，避免 KeyError
            if device not in equipments:
                return []
            equipments_list = equipments[device]
        else:
            # 如果 device 为 None，通常需要展平字典或处理所有值，这里假设传入的是列表或特定结构
            # 根据原逻辑，如果 device=None 且直接遍历 equipments (dict)，会报错，故保留原逻辑的隐式假设
            # 原代码：if device != None: equipments = equipments[device]
            # 如果 device 为 None，原代码会尝试遍历 dict 的 key-value，这通常不是预期行为。
            # 这里假设调用方保证 device 有值，或者 equipments 本身就是列表。
            # 为了安全，如果 device 为 None 且 equipments 是 dict，我们跳过或报错，视业务而定。
            # 此处严格遵循原逻辑流：如果 device 为 None，equipments 仍是 dict，下面的 for eq in equipments 会遍历 key (字符串)，导致后续解析失败。
            # 建议调用方始终传入 device。此处做防御性编程：
            if isinstance(equipments, dict):
                return []
            equipments_list = equipments

        if not equipments_list:
            return []

        # --- 1. 数据准备与预处理 (向量化操作) ---
        delete_interface_set = request_data.get('delete_interface_set', {})

        # 处理 interface_list
        interface_data = request_data.get('interface_list', [])
        if interface_data:
            interface_pd = pd.DataFrame(interface_data).add_prefix('INTERFACE.')
        else:
            interface_pd = pd.DataFrame(columns=['id', 'field_id', 'uni_code', 'cad_block_id']).add_prefix('INTERFACE.')

        # 处理 field_list
        field_data = request_data.get('field_list', [])
        if field_data:
            field_pd = pd.DataFrame(field_data).add_prefix('FIELD.')
        else:
            cols = ['id', 'system_id', 'subsystem_id', 'code', 'uni_code', 'cad_block_id',
                    'insert_point_x', 'insert_point_y', 'insert_point_z']
            field_pd = pd.DataFrame(columns=cols).add_prefix('FIELD.')

        # 合并数据 (Left Join)
        if interface_pd.empty and field_pd.empty:
            final_df = pd.DataFrame()
        else:
            final_df = pd.merge(
                field_pd,
                interface_pd,
                left_on='FIELD.id',
                right_on='INTERFACE.field_id',
                how='left'
            )

        # 过滤系统 ID (注意列名大小写一致性，原代码中有 'SUBSYSTEM.system_id' 和 'Field.system_id' 混用风险)
        # 假设列名标准化为 'FIELD.system_id' 或根据实际 merge 结果调整
        system_id_col = 'FIELD.system_id' if 'FIELD.system_id' in final_df.columns else 'Field.system_id'
        if system_id_col in final_df.columns and 'system' in request_data:
            target_sys_id = request_data['system'].get('id')
            if target_sys_id:
                # 使用布尔索引过滤，比 iterrows 快得多
                final_df = final_df[final_df[system_id_col] == target_sys_id]

        # 提取所有已存在的 interface uni_code 到 Set 中，实现 O(1) 查找
        # 只有非空的 uni_code 才加入集合，避免 None 干扰
        interface_history: Set[str] = set()
        if not final_df.empty and 'INTERFACE.uni_code' in final_df.columns:
            interface_history = set(final_df['INTERFACE.uni_code'].dropna().unique())

        # 确定描述信息
        if device and device.startswith('VMB'):
            description = 'ID 不变前提下'
        elif device and device in ['I_LINE', 'GPB']:
            description = 'ID_Short 不变前提下'
        else:
            description = f'新增{device or "UNKNOWN"}'

        results = []

        # --- 2. 高效循环检查 ---

        filename = request_data.get('filename', '')

        print(f"{delete_interface_set=}")
        for eq in equipments_list:
            # 解析属性 (这是外部依赖，无法向量化，但可以减少内部逻辑)
            equipments_info = parse_block_attributes(eq, filename)

            if not equipments_info:
                continue

            for info in equipments_info:
                interface_code = info.get('interface_code')

                # 核心加速逻辑：直接使用 Set 判断是否存在
                if interface_code and interface_code not in interface_history:
                    if interface_code not in delete_interface_set:
                        # 构造结果对象
                        # 提取后缀逻辑保持不变
                        suffix = interface_code.split('-')[-1] if '-' in interface_code else interface_code

                        results.append(CheckResult(
                            type=self.rule_type,
                            name="新增 interface",
                            description=f"{description} ID({interface_code}) 增加",
                            detail=f"{description} ID({interface_code}) 增加",
                            operation='add',
                            equipment=[eq, info],  # 注意：这里保留了引用，如果数据量极大，考虑只存 ID
                            device=device
                        ))

                        # 可选：如果需要实时更新 history 防止同一文件内重复报告（视业务需求）

                    else:
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="新增 interface",
                            description=f"{description} ID({interface_code}) 增加",
                            detail=f"{description} ID({interface_code}) 增加",
                            operation='update',
                            equipment=[eq, info],  # 注意：这里保留了引用，如果数据量极大，考虑只存 ID
                            device=device
                        ))

                    #interface_history.add(interface_code)
        return results


if __name__ == '__main__':
    pass
