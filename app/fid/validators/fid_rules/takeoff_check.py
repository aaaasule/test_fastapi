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

pd.set_option('display.max_rows', None)


class TakeoffCSCTCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "基于SDC校验CS、CT"

    def check(self, equipments: Dict[str, List[Dict[str, Any]]],
              device: str = None,
              request_data=None) -> List[CheckResult]:
        '''
        检测takeoff 的 cs ct跟sdc是否相同
        '''

        if not device:
            raise ValueError("device 类型不能为空")

        if device != None:
            equipments = equipments[device]

        results = []

        interface_pd = pd.DataFrame.from_dict(request_data['interface_list']).add_prefix('INTERFACE.')

        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')

        system_interface_pd = pd.DataFrame.from_dict(request_data['system_interface_list']).add_prefix('SYSTEM.')

        # if interface_pd.empty:
        #     interface_pd = pd.DataFrame([], columns=['id', 'field_id', 'uni_code', 'cad_block_id', 'con_size', 'con_type']).add_prefix('INTERFACE.')
        # if field_pd.empty:
        #     field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
        #                                          'code', 'uni_code', 'cad_block_id'
        #                                          'insert_point_x', 'insert_point_y', 'insert_point_z']).add_prefix('FIELD.')

        # if system_interface_pd.empty:

        # final_df = pd.merge(
        #     field_pd,
        #     interface_pd,
        #     left_on='FIELD.id',
        #     right_on='INTERFACE.field_id',
        #     how='left'
        # )
        # interface_pd['SYSTEM.sub_system'] = interface_pd['INTERFACE.uni_code'].str.split(';').str[0]
        print(f"{system_interface_pd.columns=}")
        grouped = system_interface_pd.groupby('SYSTEM.system_code').agg({
            'SYSTEM.con_size': lambda x: list(set(x)),
            'SYSTEM.con_type': lambda x: list(set(x))
        }).reset_index()

        # print(f"{grouped['SYSTEM.system_code'].unique()=}")
        print(f"grouped-\n{grouped}")
        # exit(0)

        for eq in equipments:

            equipments_infos = parse_block_attributes(eq, request_data['filename'])
            for equipment_info in equipments_infos:

                # sub_system = equipment_info['sub_system']

                # _grouped = grouped[grouped['SYSTEM.subsystem_code'] == sub_system]

                system_code = request_data['system']['name']
                #print(f"{system_code=}")
                _grouped = grouped[grouped['SYSTEM.system_code'] == system_code]

                if _grouped.empty or \
                        (equipment_info.get('connection_size') and equipment_info.get('connection_size') not in
                         _grouped.iloc[0].to_dict().get('SYSTEM.con_size')):

                    # 如果是旧版本图纸，那么不校验cs
                    if not request_data['fab']['name'].endswith(request_data['disable_fab']) and device not in ['TAKEOFF', 'VMB_CHEMICAL', 'VMB_GASNAME']:
                        results.append(CheckResult(
                            type=self.rule_type,
                            name="基于SDC校验CS、CT",
                            description=f"CS信息与SDC中设定不符",
                            detail=f"sub_system({equipment_info['connection_size']})与"
                                   f"SDC中设定不符",
                            equipment=[eq, equipment_info],
                            device=device
                        ))
                        print(f"{_grouped.empty=} connection_size: {equipment_info.get('connection_size')}")
                if _grouped.empty or \
                        (equipment_info.get('connection_type') and equipment_info.get('connection_type') not in
                         _grouped.iloc[0].to_dict().get('SYSTEM.con_type')):
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="基于SDC校验CS、CT",
                        description=f"CT信息与SDC中设定不符",
                        detail=f"sub_system({equipment_info['connection_type']})与"
                               f"SDC中设定不符",
                        equipment=[eq, equipment_info],
                        device=device
                    ))
                    print(f"{_grouped.empty=} connection_type: {equipment_info.get('connection_type')}")
        return results


if __name__ == '__main__':
    import sys
    from pathlib import Path
    print(sys.path)
    print(Path('./').absolute().parent.parent)
    sys.path.append(str(Path('./').absolute().parent.parent.parent))
    from eld_validator.fid_parse import parse_dxf

    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PA^FAB1^F2.dxf'  # take off
    #dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PC^FAB2^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB1^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB2^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.ES^FAB2^F2.dxf'

    eqps = parse_dxf(dxf_path)

    request_data = {'field&interface':{'N208V-3P;FAB2F2-BUS-F21-1-N2-15-Q10':
         {'sub_system': 'U-3P;FAB2F2-F22-1-2I-LINE-U2-05-63D2716', 'conSize':1, 'conType':2}}
     }
    for eq in eqps:

        rule = TakeoffCSCTCheck()
        results = rule.check(eqps[eq], device=eq, request_data=request_data)

        for r in results:
            print(r)


