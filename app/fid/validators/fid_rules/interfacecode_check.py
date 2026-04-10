from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import  CheckResult

from app.fid.utils.parse_block_attributes import parse_block_attributes


class FIDInterfaceCodeRule(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = 'ID规范性错误'

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

    def get_id_value(self, eq: Dict[str, Any], device: str) -> str:
        """根据设备类型获取对应的 ID 字段值"""
        field_name = self.ID_FIELD_MAP.get(device)
        # print(f"{field_name=}")
        if not field_name:
            raise ValueError(f"不支持的设备类型: {device}")
        return eq.get(field_name)

    def parse_interface_code(self, id_value: str, device: str):
        """根据设备类型解析 ID 字符串（原 INTERFACE_CODE/ID/ID_SHORT）"""
        if not isinstance(id_value, str) or not id_value.strip():
            return None

        parts = [p.strip() for p in id_value.split(';')]  # 先 strip 每一段
        n = len(parts)

        # 辅助函数：检查指定索引的 part 是否有效（非空）
        def is_empty(idx):
            return idx < len(parts) and parts[idx] == ''

        # print(f"parse_interface_code - {parts=} {[is_empty(i) for i in range(4)]}")

        if device == 'TAKEOFF':
            if n != 4 or any(is_empty(i) for i in range(4)):
                return None
            return {
                'sub_system': parts[0],
                'building_level': parts[1],
                'field': parts[2],
                'id': parts[3]
            }

        elif device in ['VMB_CHEMICAL', 'VMB_GASNAME']:
            if n < 3 or is_empty(0) or is_empty(1):
                return None
            # parts[2:] 可以包含空段吗？根据业务决定。
            # 如果 field 允许为空或含空段，保留；否则可加校验。
            field = ';'.join(parts[2:])
            if not field:  # 如果业务要求 field 非空
                return None
            return {
                'sub_system': parts[0],
                'building_level': parts[1],
                'field': field
            }

        elif device in ['I_LINE', 'GPB', 'NEW_INTER_']:
            if n < 2 or is_empty(0) or is_empty(1):
                return None
            return {
                'sub_system': parts[0],
                'building_level': parts[1]
            }

        else:
            # 未知设备类型，默认只取前两段（保守处理）

            if n < 2 or is_empty(0) or is_empty(1):
                return None
            return {
                'sub_system': parts[0],
                'building_level': parts[1]
            }

    def validate_equipment(self, eq: Dict[str, Any], device: str, request_data: Dict[str, Any]) -> bool:
        # print(f"validate_equipment - {eq=}")
        id_value = self.get_id_value(eq, device)
        # if id_value and (id_value.startswith(';') or id_value.endswith(';')):
        # print(f"{id_value=} {id_value is None} {id_value == None} {str(id_value) == 'None'}")
        if id_value is None:
            return True

        parsed = self.parse_interface_code(id_value, device)
        # print(f"{device=} {id_value=} {parsed=}")
        if parsed is None:
            return False

        required_keys = self.REQUIRED_FIELDS.get(device, [])
        for key in required_keys:
            if parsed.get(key) != request_data.get(key):
                return False
        return True

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

        # print(f"{equipments=}")
        for eq in equipments:

            equipment_info = parse_block_attributes(eq, request_data['filename'])[0]
            equipment_info = {k: equipment_info.get(k) for k in equipment_info if
                              k in ['building_level', 'field', 'sub_system', 'id']}
            is_valid = self.validate_equipment(eq, device, equipment_info)

            if not is_valid:
                ic = self.get_id_value(eq, device)

                if device == 'TAKEOFF':
                    name = 'Interface_Code规范性错误'
                    description = "未包含四个字段，{sub_system};{building_level};{field};{id}"
                elif device.startswith('VMB'):
                    name = 'ID规范性错误'
                    description = "未包含三个字段，{sub_system};{building_level};{field} "
                else:
                    name = 'ID规范性错误'
                    description = "未包含两个字段，{sub_system};{building_level} "

                detail = f"{self.ID_FIELD_MAP.get(device)} '{ic}' 不符合 {device} 类型的格式或字段要求"
                results.append(CheckResult(equipment=[eq],
                                           description=description,
                                           type=self.rule_type,
                                           name=name,
                                           detail=detail,
                                           device=device))
                print(f"{device=} {self.ID_FIELD_MAP.get(device)} '{ic}' 不符合格式或字段要求")
            else:
                pass

        print(f"ID规范性错误{results=}")
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

    for eq in eqps:

        rule = InterfaceCodeRule()
        results = rule.check(eqps[eq], device=eq)

        print(eq, len(results))
        for r in results:
            print(r)

