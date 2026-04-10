from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import  CheckResult

class VMBIdChemicalCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "ID与chemicalName不匹配"

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

        for eq in equipments:
            #print(eq)

            if 'CHEMICALNAME' in eq:

                #if request_data['fab']['name']
                if request_data['fab']['name'].endswith(request_data['disable_fab']):
                    continue

                if eq.get('ID') and eq['CHEMICALNAME']:
                    sub_system = eq['ID'].split(';')[0]
                    if eq['CHEMICALNAME'] != sub_system:
                        results.append(CheckResult(
                                type=self.rule_type,
                                name="ID与chemicalName不匹配",
                                description=f"ID中subsystem与chemicalname字段未保持一致",
                                detail=f"ID中subsystem {sub_system}与chemicalname {eq['CHEMICALNAME']}字段保持一致",
                                equipment=[eq],
                                device=device
                            ))
                # else:
                #     results.append(CheckResult(
                #         type=self.rule_type,
                #         name="ID与chemicalName不匹配",
                #         description=f"ID中subsystem与chemicalname字段未保持一致",
                #         detail=f"ID中subsystem {eq.get('ID')}与chemicalname {eq['CHEMICALNAME']}字段保持一致",
                #         equipment=[eq]
                #     ))

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
         {'sub_system': 'U-3P;FAB2F2-F22-1-2I-LINE-U2-05-63D2716'}}
     }
    for eq in eqps:
        if not eq.startswith('VMB'):
            continue

        rule = InterfaceCodeRule()
        results = rule.check(eqps, device=eq, request_data=request_data)

        for r in results:
            print(r)

