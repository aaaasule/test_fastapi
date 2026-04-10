from typing import List, Any, Dict
import sys
from pathlib import Path
import pandas as pd
import time

# 将项目根目录加入 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult
from app.fid.utils.parse_block_attributes import parse_block_attributes

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

import json

class BlockRemovedCheck(BaseRule):
    rule_type = "warning"
    rule_name = '图块删除'
    DEFAULT_FIELDS = ["cad_block_name", "layer", "insert_point_x", "insert_point_y", "insert_point_z", "angle",
                      "true_color", "cad_block_id", "distribution_box"]

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data=None) -> List[
        CheckResult]:
        start_time = time.time()

        if isinstance(equipments, dict):
            equipments = equipments[device]
        if len(equipments) == 0:
            return []

        results = []
        description = "和上一版数据相比图块删除"

        # --- 1. 数据准备 (保持原有逻辑，修复列定义) ---

        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')
        subsystem_pd = pd.DataFrame.from_dict(request_data['subsystem_list']).add_prefix('SUBSYSTEM.')

        # 修复：补全缺失的逗号
        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
                                                 'code', 'uni_code', 'cad_block_id',
                                                 'insert_point_x', 'insert_point_y', 'insert_point_z']).add_prefix(
                'FIELD.')

        if subsystem_pd.empty:
            subsystem_pd = pd.DataFrame([], columns=['id', 'system_id',
                                                     'code', 'uni_code', 'cad_block_id',
                                                     'insert_point_x', 'insert_point_y', 'insert_point_z']).add_prefix(
                'SUBSYSTEM.')


        # interface_pd = interface_pd[interface_pd['INTERFACE.status'] != 'not_existing_in_fid']
        # field_pd = field_pd[field_pd['FIELD.status'] != 'not_existing_in_fid']


        final_df = pd.merge(
            subsystem_pd,
            field_pd,
            left_on='SUBSYSTEM.id',
            right_on='FIELD.subsystem_id',
            how='left'
        )

        print(field_pd.shape, subsystem_pd.shape, final_df.shape)

        debug_dir = Path(__file__).parent.parent.parent / 'temp_debug'
        debug_dir.mkdir(exist_ok=True)


        # interface_pd.to_excel(debug_dir / f'{device}_block_remove_interface_pd.xlsx')
        # field_pd.to_excel(debug_dir / f'{device}_block_remove_field_pd.xlsx')
        # subsystem_pd.to_excel(debug_dir / f'{device}_block_remove_subsystem_pd.xlsx')
        # field_interface_df.to_excel(debug_dir / f'{device}_block_remove_field_interface_df.xlsx')
        # final_df.to_excel(debug_dir / f'{device}_block_remove_final_df.xlsx')

        # 系统过滤
        if 'SUBSYSTEM.system_id' in final_df.columns and request_data.get('system', {}).get('id'):
            final_df = final_df[final_df['SUBSYSTEM.system_id'] == request_data['system']['id']]

        print(f"{final_df.shape=}")
        #final_df.to_excel(debug_dir / f"{device}_block_remove_final_df_system={request_data['system']['id']}.xlsx")
        # --- 2. 高效收集现有设备信息 (关键优化点) ---
        # 原代码：循环 + 列表追加 -> 慢
        # 新代码：列表推导式 + 批量构建 DataFrame -> 快

        all_infos = []



        for eq in equipments:
            try:
                infos = parse_block_attributes(eq, request_data['filename'])
                # print(f"{eq=}")
                # print(f"{infos=}")
                if infos:
                    all_infos.extend(infos)
                else:
                    print(f"解析接口失败{eq=}")
            except Exception as e:
                # 防止单个解析失败导致整个流程中断
                print(f"[WARN] Parse failed for eq: {e}")
                continue


        # 构建现有设备的 DataFrame
        equipments_pd = pd.DataFrame(all_infos) if all_infos else pd.DataFrame()

        #equipments_pd.to_excel(debug_dir / f'{device}_block_remove_equipments_pd.xlsx')
        print(f"{equipments_pd.shape=}")
        # 【核心优化】：将现有的 field_code 转换为 Set，实现 O(1) 查找
        # 注意：原代码用的是 'field_code'，请确保 parse_block_attributes 返回的字典里有这个 key
        # 如果返回的是 'interface_code' 或其他，请相应修改下面的 key
        existing_codes_set = set()
        if not equipments_pd.empty and 'field_code' in equipments_pd.columns:
            existing_codes_set = set(equipments_pd['field_code'].dropna().unique())



        # 1. 保存集合内容 (JSON 格式，易读)
        set_file = debug_dir / 'existing_codes_set.json'
        with open(set_file, 'w', encoding='utf-8') as f:
            json.dump(list(existing_codes_set), f, ensure_ascii=False, indent=2)
        # --- 3. 快速比对 (关键优化点) ---
        # 原代码：循环 final_df 索引，每次计算 unique() -> O(N*M)
        # 新代码：去重后直接利用 Set 判断 -> O(N)

        if not final_df.empty:
            # 先去重，避免重复报警
            final_df_unique = final_df.drop_duplicates(subset=['FIELD.uni_code'], keep='first')

            #final_df_unique.to_excel(debug_dir / f'{device}_block_remove_finaldf.xlsx')
            # 筛选出那些 uni_code 不在现有集合中的行
            # 使用 apply 或者布尔索引进行向量化操作
            mask = final_df_unique['FIELD.uni_code'].apply(
                lambda x: x not in existing_codes_set if pd.notna(x) else False)
            deleted_rows = final_df_unique[mask]

            #deleted_rows.to_excel(debug_dir / f'{device}_block_remove_delete_rows.xlsx')
            print(f"{deleted_rows.shape=}")
            for idx, row in deleted_rows.iterrows():
                field_code = row['FIELD.uni_code']

                # 构造结果对象
                # 提取 FIELD. 前缀的列
                block_eq = {}
                for k, v in row.to_dict().items():
                    if k.startswith('FIELD.'):
                        block_eq[k.split('FIELD.')[1]] = v

                # 转大写 (模拟原逻辑)
                _result_eq = {k.upper(): v for k, v in block_eq.items()}

                results.append(CheckResult(
                    type=self.rule_type,
                    name="图块删除",
                    description=description,
                    detail=f"检测到图块 {field_code} 已被删除",
                    equipment=[_result_eq],
                    operation='delete',
                    field_or_interface='field',
                    device=device
                ))

                # 可选：少量打印，避免刷屏
                print(f"block delete - {field_code=}")

        end_time = time.time()
        print(f"[PERF] BlockRemovedCheck 耗时：{(end_time - start_time) * 1000:.2f} ms, 发现删除数：{len(results)}")

        return results


if __name__ == '__main__':
    pass
