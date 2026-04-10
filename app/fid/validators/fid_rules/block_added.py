from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import  CheckResult

from app.fid.utils.parse_block_attributes import parse_block_attributes

import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)


class BlockAddCheck(BaseRule):
    rule_name = '图块添加'
    rule_type = "warning"

    DEFAULT_FIELDS = ["cad_block_name", "layer", "insert_point_x", "insert_point_y", "insert_point_z", "angle",
                      "true_color", "cad_block_id", "distribution_box"]

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data=None) -> List[
        CheckResult]:
        """
        对所有 equipment 执行 INTERFACE_CODE 校验。

        Args:
            equipments: 二维列表，通常外层是区域/系统，内层是设备
            device: 设备类型，如 'TAKEOFF', 'VMB' 等

        Returns:
            List[CheckResult]
        """

        if device != None:
            equipments = equipments[device]

        if len(equipments) == 0:
            return []

        results = []

        delete_field_set = request_data['delete_field_set']

        # print(f"{request_data['interface_list']=}")

        #interface_pd = pd.DataFrame.from_dict(request_data['interface_list']).add_prefix('INTERFACE.')

        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')

        # if interface_pd.empty:
        #     interface_pd = pd.DataFrame([], columns=['id', 'field_id', 'uni_code', 'cad_block_id']).add_prefix(
        #         'INTERFACE.')
        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
                                                 'code', 'uni_code', 'cad_block_id'
                                                                     'insert_point_x', 'insert_point_y',
                                                 'insert_point_z']).add_prefix('FIELD.')

        # if interface_pd.empty or field_pd.empty:
        #     print(f"{interface_pd.empty=} {field_pd.empty=}")
        #     return []

        # final_df = pd.merge(
        #     field_pd,
        #     interface_pd,
        #     left_on='FIELD.id',
        #     right_on='INTERFACE.field_id',
        #     how='left'
        # )
        final_df = field_pd

        # print(f"{final_df=}")
        if device == 'TAKEOFF':
            description = "和上一版数据相比图块新增"
        elif device.startswith('VMB'):
            description = '和上一版数据相比图块新增'
        else:
            description = '和上一版数据相比图块新增'

        print(f"{final_df.shape=}")
        #final_df.to_excel(Path(__file__).parent.parent.parent / 'temp_uploads' / 'block_add_final_df_1.xlsx')
        final_df = final_df.drop_duplicates(subset=['FIELD.uni_code'], keep='first')
        print(f"{final_df.shape=}")
        #print(f"{list(final_df['FIELD.uni_code'].unique())=}")
        #final_df.to_excel(Path(__file__).parent.parent.parent / 'temp_uploads' / 'block_add_final_df_2.xlsx')
        current_block = []

        field_uni_code_unique = set(final_df['FIELD.uni_code'].unique())
        print(f"{field_uni_code_unique=}")
        print(f"{len(field_uni_code_unique)=}")

        print(f"{delete_field_set=}")
        for eq in equipments:
            # print(eq)

            equipments_info = parse_block_attributes(eq, request_data['filename'])

            #print(f"[block add]{equipments_info=}")
            if len(equipments_info) > 0:
                field_name = equipments_info[0]['field_code']

                current_block.append(field_name)

                if field_name not in field_uni_code_unique:
                    if field_name not in delete_field_set:
                        #eq['detail'] = description
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="图块新增",
                            description=description,
                            detail=description,
                            equipment=[eq],
                            operation='add',
                            field_or_interface='field',
                            device=device
                        ))
                        print(f"block add - {field_name=}")
                    else:
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="图块新增",
                            description=description,
                            detail=description,
                            equipment=[eq],
                            operation='update',
                            field_or_interface='field',
                            device=device
                        ))
                        print(f"block update but add - {field_name=}")

            else:
                print(f'解析接口失败， 不添加{eq=}')
        #print(f"{current_block=}")
        return results


if __name__ == '__main__':
    pass
