from typing import List, Any, Dict, Set
import sys
from pathlib import Path
import pandas as pd

# 路径设置
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult
from app.fid.utils.parse_block_attributes import parse_block_attributes

# 全局设置一次
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

import json

class InterfaceRemoveCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "warning"
    rule_name = '删除 interface'

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data: Dict = None) -> List[
        CheckResult]:
        """
        优化版：检测已存在于数据库但不在当前 DXF 文件中的 Interface (即被删除的接口)。

        加速策略：
        1. 将 DXF 解析出的所有 interface_code 放入一个 Set (current_codes)。
        2. 将数据库中的 interface_code 放入另一个 Set (db_codes)。
        3. 直接使用集合差集 (db_codes - current_codes) 找出被删除的项。
        4. 避免在循环中调用 unique() 或进行线性搜索。
        5. 移除所有调试打印语句。
        """

        print(f"{device=}")
        if isinstance(equipments, dict):
            equipments = equipments[device]
        if len(equipments) == 0:
            return []

        # 2. 准备数据库侧数据 (DataFrame 构建与合并)
        # 使用 get 避免 KeyError，提供默认空列表
        interface_list = request_data.get('interface_list', [])
        field_list = request_data.get('field_list', [])
        subsystem_list = request_data.get('subsystem_list', [])

        # 构建 DataFrame
        if interface_list:
            interface_pd = pd.DataFrame(interface_list).add_prefix('INTERFACE.')
        else:
            interface_pd = pd.DataFrame(columns=['id', 'field_id', 'uni_code', 'cad_block_id']).add_prefix('INTERFACE.')

        if field_list:
            field_pd = pd.DataFrame(field_list).add_prefix('FIELD.')
        else:
            cols = ['id', 'system_id', 'subsystem_id', 'code', 'uni_code', 'cad_block_id',
                    'insert_point_x', 'insert_point_y', 'insert_point_z']
            field_pd = pd.DataFrame(columns=cols).add_prefix('FIELD.')

        if subsystem_list:
            subsystem_pd = pd.DataFrame(subsystem_list).add_prefix('SUBSYSTEM.')
        else:
            cols = ['id', 'system_id', 'code', 'uni_code', 'cad_block_id',
                    'insert_point_x', 'insert_point_y', 'insert_point_z']
            subsystem_pd = pd.DataFrame(columns=cols).add_prefix('SUBSYSTEM.')


        # interface_pd = interface_pd[interface_pd['INTERFACE.status'] == 'not_existing_in_fid']
        # field_pd = field_pd[field_pd['FIELD.status'] == 'not_existing_in_fid']


        field_interface_df = pd.merge(
            field_pd, interface_pd,
            left_on='FIELD.id', right_on='INTERFACE.field_id', how='left'
        )


        final_df = pd.merge(
            subsystem_pd, field_interface_df,
            left_on='SUBSYSTEM.id', right_on='FIELD.subsystem_id', how='left'
        )

        print(f"{final_df.shape=}")
        # 过滤系统 ID
        if not final_df.empty and 'SUBSYSTEM.system_id' in final_df.columns:
            target_sys_id = request_data.get('system', {}).get('id')
            if target_sys_id is not None:
                final_df = final_df[final_df['SUBSYSTEM.system_id'] == target_sys_id]

        if final_df.empty:
            return []

        print(f"{final_df.shape=}")


        # 3. 解析当前 DXF 文件中的s所有 Interface Code (构建集合)
        # 这一步是必须的，我们需要知道“现在有什么”，从而推断“少了什么”
        current_interface_codes: Set[str] = set()

        # # 遍历所有设备节点解析属性
        # # 注意：原代码逻辑是遍历 equipments 字典的所有值
        # for _device_key, _equipments_list in equipments.items():
        for eq in equipments:
            # 解析块属性
            equipments_info = parse_block_attributes(eq, request_data.get('filename', ''))
            if not equipments_info:
                print(f"解析接口错误，跳过")
                continue

            # 提取 interface_code 加入集合
            for info in equipments_info:
                code = info.get('interface_code')
                if code:
                    current_interface_codes.add(code)


        debug_dir = Path(__file__).parent.parent.parent / 'temp_debug'
        debug_dir.mkdir(exist_ok=True)
        set_file = debug_dir / 'current_interface_codes.json'
        with open(set_file, 'w', encoding='utf-8') as f:
            json.dump(list(current_interface_codes), f, ensure_ascii=False, indent=2)

        # 4. 核心加速逻辑：集合差集运算
        # 获取数据库中所有的 uni_code (去重且去除空值)
        db_codes_series = final_df['INTERFACE.uni_code'].dropna()
        if db_codes_series.empty:
            return []

        db_codes_set = set(db_codes_series.unique())
        set_file = debug_dir / 'db_codes_set.json'
        with open(set_file, 'w', encoding='utf-8') as f:
            json.dump(list(db_codes_set), f, ensure_ascii=False, indent=2)

        # 计算差集：在数据库中但不在当前文件中的代码 = 被删除的代码
        deleted_codes = db_codes_set - current_interface_codes

        if not deleted_codes:
            return []

        # 5. 生成结果报告
        results = []

        # 确定描述信息
        if device.startswith('VMB'):
            description = 'ID 不变前提下'
        elif device in ['I_LINE', 'GPB']:
            description = 'ID_Short 不变前提下'
        else:
            description = f'删除 {device}'

        # 为了快速定位被删除代码对应的详细信息 (如 field_id, subsystem 等)，
        # 我们建立一个映射：code -> 第一行匹配的记录字典
        # 注意：如果有重复 code，取第一个即可用于报错展示
        code_to_record_map = {}
        for _, row in final_df.iterrows():
            code = row['INTERFACE.uni_code']
            if pd.isna(code):
                continue
            if code not in code_to_record_map:
                # 提取 INTERFACE 前缀的字段
                interface_data = {k.split('INTERFACE.', 1)[1]: v
                                  for k, v in row.to_dict().items()
                                  if k.startswith('INTERFACE.')}
                field_data = {k.split('FIELD.', 1)[1]: v
                                  for k, v in row.to_dict().items()
                                  if k.startswith('FIELD.')}
                code_to_record_map[code] = [field_data, interface_data]

        # 遍历差集生成结果
        for code in deleted_codes:
            if code in code_to_record_map:
                delete_info = code_to_record_map[code]

                results.append(CheckResult(
                    type=self.rule_type,
                    name="删除 interface",
                    description=f"{description} ID({code}) 删除",
                    detail=f"{description} ID({code}) 删除",
                    operation='delete',
                    # 注意：删除操作通常没有对应的当前设备对象 (eq)，因为设备已经不存在了。
                    # 原代码这里的 eq 变量作用域有误，这里传入删除的记录详情更合理。
                    equipment=delete_info,
                    device=device
                ))

                print(f"interface delete - {code=}")
        return results


if __name__ == '__main__':
    pass
