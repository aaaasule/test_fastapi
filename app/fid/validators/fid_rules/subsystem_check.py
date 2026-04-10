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


class SubsystemCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "基于SDC校验Sub_system"

    ID_FIELD_MAP = {
        'TAKEOFF': 'INTERFACE_CODE',
        'VMB_CHEMICAL': 'ID',
        'VMB_GASNAME': 'ID',
        'I_LINE': 'ID',
        'GPB': 'ID',
        'NEW_INTER_': 'ID',
    }

    # 设备类型 → 所需字段列表
    REQUIRED_FIELDS = {
        'TAKEOFF': ['sub_system', 'building_level', 'field', 'id'],
        'VMB_CHEMICAL': ['sub_system', 'building_level', 'field'],
        'VMB_GASNAME': ['sub_system', 'building_level', 'field'],
        'I_LINE': ['sub_system', 'building_level'],
        'GPB': ['sub_system', 'building_level'],
        'NEW_INTER_': ['sub_system', 'building_level'],
    }

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
        if not device:
            raise ValueError("device 类型不能为空")

        if device != None:
            equipments = equipments[device]

        results = []
        # request_data = request_data['field&interface']

        subsystem_pd = pd.DataFrame.from_dict(request_data['subsystem_list']).add_prefix('SUBSYSTEM.')
        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')

        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
                                                 'code', 'uni_code', 'cad_block_id'
                                                                     'insert_point_x', 'insert_point_y',
                                                 'insert_point_z']).add_prefix('FIELD.')
        if subsystem_pd.empty:
            subsystem_pd = pd.DataFrame([], columns=['id', 'system_id', 'code', 'is_slurry']).add_prefix('SUBSYSTEM.')

        # field_and_subsystem_pd = pd.merge(
        #     field_pd,
        #     subsystem_pd,
        #     left_on='FIELD.subsystem_id',
        #     right_on='SUBSYSTEM.id',
        #     how='left'
        # )

        for eq in equipments:

            equipments_info = parse_block_attributes(eq, request_data['filename'])

            for info in equipments_info:

                field_code = info['field']

                # target_df = field_and_subsystem_pd[field_and_subsystem_pd['FIELD.code'] == field_code]

                if info['sub_system'] and info['sub_system'] not in subsystem_pd['SUBSYSTEM.code'].unique():
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="基于SDC校验Sub_system",
                        description=f"sub_system与SDC中设定不符",
                        detail=f"sub_system({info['sub_system']})与SDC({subsystem_pd['SUBSYSTEM.code'].unique()})中设定不符",
                        # equipment=[eq, info]
                        equipment=[eq],
                        device=device
                    ))

                    break
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
         {'sub_system': 'U-3P;FAB2F2-F22-1-2I-LINE-U2-05-63D2716'}}
     }

    for eq in eqps:

        rule = SubsystemCheck()
        results = rule.check(eqps, device=eq, request_data=request_data)

        for r in results:
            print(r)

