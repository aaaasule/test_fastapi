from typing import List, Any, Dict

import pandas as pd

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import  CheckResult

from app.fid.utils.parse_block_attributes import parse_block_attributes

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)

class VMBSlurryCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "Slurry校验（I/O.X点位错误）"

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data = None) -> List[CheckResult]:
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


        subsystem_pd = pd.DataFrame.from_dict(request_data['subsystem_list']).add_prefix('SUBSYSTEM.')
        interface_pd = pd.DataFrame.from_dict(request_data['interface_list']).add_prefix('INTERFACE.')
        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')

        if interface_pd.empty:
            interface_pd = pd.DataFrame([], columns=['id', 'field_id', 'uni_code', 'cad_block_id']).add_prefix('INTERFACE.')
        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
                                                 'code', 'uni_code', 'cad_block_id'
                                                 'insert_point_x', 'insert_point_y', 'insert_point_z']).add_prefix('FIELD.')
        if subsystem_pd.empty:
            subsystem_pd = pd.DataFrame([], columns=['id', 'system_id', 'code', 'is_slurry']).add_prefix('SUBSYSTEM.')

        merged_1 = pd.merge(
            field_pd,
            subsystem_pd,
            left_on='FIELD.subsystem_id',
            right_on='SUBSYSTEM.id',
            how='left'
        )

        final_df = pd.merge(
            merged_1,
            interface_pd,
            left_on='FIELD.id',
            right_on='INTERFACE.field_id',
            how='left'
        )

        #print(final_df)
        # raise Exception
        #print(f"{device=}")
        #print(f"{equipments=}")
        # equipments[0]['ID.A'] = 1
        # if len(equipments) > 0:
        #     equipments = [equipments[0]]
        #print(f"{equipments=}")

        for eq in equipments:
            if 'CHEMICALNAME' in eq:
            #if True:
                equipments_info = parse_block_attributes(eq, request_data['filename'])

                for info in equipments_info:
                    interface_code = info['interface_code']
                    slurry_data = final_df[final_df['INTERFACE.uni_code'] == interface_code]

                    if slurry_data.empty:
                        is_slurry = 0
                    else:
                        is_slurry = slurry_data.iloc[0]['SUBSYSTEM.is_slurry']
                    #print(f"{is_slurry=} {slurry_data.empty=}")
                    #if int(is_slurry) == 0 and info['interface_code'] and info['I/O'] != info['interface_code'].split('-')[-1]:
                    if int(is_slurry) == 0 and info['interface_code'] and info['I/O'] != info['IDx']:
                        # description = f"I/O.{info['x']}与ID.{info['x']}({info['IDx']})未保持一致"
                        # results.append(CheckResult(
                        #     type=self.rule_type,
                        #     name="I/O.X点位错误",
                        #     #description=f"I/O.{info['x']}点位错误",
                        #     description=description,
                        #     detail=f"",
                        #     equipment=[eq, info]
                        # ))
                        pass
                    elif int(is_slurry) == 1 and info['IDx'] is None:
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="必填项错误",
                            description=f"ID.{info['x']}未填写",
                            detail=f"ID.{info['x']}未填写",
                            equipment=[eq, info],
                            device=device
                        ))

        return results


if __name__ == '__main__':
    import sys
    from pathlib import Path
    print(sys.path)
    print(Path('./').absolute().parent.parent)
    sys.path.append(str(Path('./').absolute().parent.parent.parent))
    from eld_validator.fid_parse import parse_dxf

    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PA^FAB1^F2.dxf'  # take off
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PC^FAB2^F2.dxf'
    #dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB1^F2.dxf' #VMB_GASNAME\ NEW_INTER_
    #dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB2^F2.dxf' #GASNAME
    #dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.ES^FAB2^F2.dxf'

    eqps = parse_dxf(dxf_path)

    request_data = {'field&interface':{'N208V-3P;FAB2F2-BUS-F21-1-N2-15-Q10':
         {'sub_system': 'U-3P;FAB2F2-F22-1-2I-LINE-U2-05-63D2716'}},
        'subsystem_list':[
            {'id':1, 'systemId':1, 'code':'sub1', 'isSlurry':0},
            {'id':2, 'systemId':2, 'code':'sub2', 'isSlurry':1}
        ],
        'field_list':[
            {'id':1, 'system_id':1, 'subsystem_id':1, 'uni_code': '2a18B-W;19-A'},
            {'id':2, 'system_id':1, 'subsystem_id':1, 'uni_code': '2a18B-W;20-A'},
            {'id':3, 'system_id':1, 'subsystem_id':1, 'uni_code': '2a18B-E;22-A'},
            {'id':4, 'system_id':1, 'subsystem_id':2, 'uni_code': '2a18B-W;08-A'},
            {'id':5, 'system_id':1, 'subsystem_id':2, 'uni_code': '2a17B-E;21-A'},
            {'id':6, 'system_id':1, 'subsystem_id':2, 'uni_code': '2a17B-E;22-A'}
        ],
        'interface_list':[
            {'id':1, 'field_id':1, 'uni_code':'IPA;FAB2F2;2a18B-W;19'},
            {'id':2, 'field_id':2, 'uni_code':'IPA;FAB2F2;2a18B-W;20-D'},
            {'id':3, 'field_id':3, 'uni_code':'IPA;FAB2F2;2a18B-E;22-D'},
            {'id':4, 'field_id':4, 'uni_code':'HNO3-70%;FAB2F2;2a18B-W;08-A'},
            {'id':5, 'field_id':5, 'uni_code':'NH4OH-29%;FAB2F2;2a17B-E;21-A'},
            {'id':6, 'field_id':6, 'uni_code':'NH4OH-29%;FAB2F2;2a17B-E;22-A'},
        ]
     }

    for eq in eqps:
        if not eq.startswith('VMB'):
            continue

        rule = InterfaceCodeRule()

        results = rule.check(eqps, device=eq, request_data=request_data)

        for r in results:
            print(r)

