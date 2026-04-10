from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import  CheckResult

class FidUniqueCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "ID唯一性错误"
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
        if not device:
            raise ValueError("device 类型不能为空")

        if device != None:
            equipments = equipments[device]

        id_seen = {}
        results = []
        repeat = False

        for equipment in equipments:
            #print(f"[ID唯一性错误]{equipment=}")
            #print(f"{id_seen=}")

            if device in ['NEW_INTER_', 'I_LINE', 'GPB'] and equipment.get('ID_SHORT'):
                #print(f"{equipment.get('ID_SHORT')=}")
                # if equipment['ID_SHORT'] not in id_seen:
                #     id_seen[equipment['ID_SHORT']] = [equipment]
                # else:
                #     id_seen[equipment['ID_SHORT']].append(equipment)
                #     results.append(CheckResult(
                #         type=self.rule_type,
                #         name="ID_Short唯一性错误",
                #         description=f"图纸中ID_Short重复",
                #         detail=f"{equipment['ID_SHORT']}",
                #         equipment=[equipment]
                #     ))
                if equipment['ID_SHORT'] not in id_seen:
                    id_seen[equipment['ID_SHORT']] = [
                        CheckResult(
                            type=self.rule_type,
                            name="ID_Short唯一性错误",
                            description=f"图纸中ID_Short重复",
                            detail=f"图纸中ID_Short({equipment['ID_SHORT']})重复",
                            equipment=[equipment],
                            device=device
                        )
                    ]
                else:
                    id_seen[equipment['ID_SHORT']].append(
                        CheckResult(
                            type=self.rule_type,
                            name="ID_Short唯一性错误",
                            description=f"图纸中ID_Short重复",
                            detail=f"图纸中ID_Short({equipment['ID_SHORT']})重复",
                            equipment=[equipment],
                            device=device
                        )
                    )

            elif device in ['VMB_CHEMICAL', 'VMB_GASNAME'] and equipment.get('ID'):
                #print(f"{equipment.get('ID')=}")
                # if equipment['ID'] not in id_seen:
                #     id_seen[equipment['ID']] = [equipment]
                # else:
                #     id_seen[equipment['ID']].append(equipment)
                #     results.append(CheckResult(
                #         type=self.rule_type,
                #         name="ID唯一性错误",
                #         description=f"图纸中ID重复",
                #         detail=f"{equipment['ID']}",
                #         equipment=[equipment]
                #     ))
                if equipment['ID'] not in id_seen:
                    id_seen[equipment['ID']] = [
                        CheckResult(
                            type=self.rule_type,
                            name="ID唯一性错误",
                            description=f"图纸中ID重复",
                            detail=f"图纸中ID({equipment['ID']})重复",
                            equipment=[equipment],
                            device=device
                        )
                    ]
                else:
                    id_seen[equipment['ID']].append(
                        CheckResult(
                            type=self.rule_type,
                            name="ID唯一性错误",
                            description=f"图纸中ID重复",
                            detail=f"图纸中ID({equipment['ID']})重复",
                            equipment=[equipment],
                            device=device
                        )
                    )
            elif device in ['TAKEOFF'] and equipment.get('INTERFACE_CODE'):
                #print(f"{equipment.get('INTERFACE_CODE')=}")
                # if equipment['INTERFACE_CODE'] not in id_seen:
                #     id_seen[equipment['INTERFACE_CODE']] = [equipment]
                # else:
                #     id_seen[equipment['INTERFACE_CODE']].append(equipment)
                    # results.append(CheckResult(
                    #     type=self.rule_type,
                    #     name="Interface_Code唯一性错误",
                    #     description=f"图纸中Interface_Code重复",
                    #     detail=f"{equipment['INTERFACE_CODE']}",
                    #     equipment=[equipment]
                    # ))
                if equipment['INTERFACE_CODE'] not in id_seen:
                    id_seen[equipment['INTERFACE_CODE']] = [
                        CheckResult(
                            type=self.rule_type,
                            name="Interface_Code唯一性错误",
                            description=f"图纸中Interface_Code重复",
                            detail=f"图纸中Interface_Code({equipment['INTERFACE_CODE']})重复",
                            equipment=[equipment],
                            device=device
                        )
                    ]
                else:
                    id_seen[equipment['INTERFACE_CODE']].append(
                        CheckResult(
                            type=self.rule_type,
                            name="Interface_Code唯一性错误",
                            description=f"图纸中Interface_Code重复",
                            detail=f"图纸中Interface_Code({equipment['INTERFACE_CODE']})重复",
                            equipment=[equipment],
                            device=device
                        )
                    )
        for repeat_id in id_seen:
            if len(id_seen[repeat_id]) > 1:
                for cr in id_seen[repeat_id]:
                    results.append(cr)
                    print(f"{cr.detail}")
        return results


if __name__ == '__main__':
    import os
    import sys
    from pathlib import Path
    print(sys.path)
    print(Path('./').absolute().parent.parent)
    sys.path.append(str(Path('./').absolute().parent.parent.parent))
    from eld_validator.fid_parser import fid_parse_dxf

    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PA^FAB1^F2.dxf'  # take off
    #dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PC^FAB2^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB1^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB2^F2.dxf'
    dxf_path = os.path.abspath(r"C:\Users\w8856\Desktop\新建文件夹\FID\数据错误\YMTC^FID.PB^FAB2^F2.dxf")


    eqps = fid_parse_dxf(dxf_path)

    for k in eqps:

        rule = FidUniqueCheck()
        results = rule.check(eqps[k], device=k)
        print(results)


