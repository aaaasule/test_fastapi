from typing import List, Any, Dict
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult

from app.fid.utils.parse_block_attributes import parse_block_attributes


class BuildingLevelCheck(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = 'building_level字段错误'

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

        results = []

        building = request_data['building']['name']
        level = request_data['building_level']['name']
        building_level = f"{building}{level}"
        for eq in equipments:

            equipment_info = parse_block_attributes(eq, request_data['filename'])[0]

            if building_level not in equipment_info['building_level']:

                results.append(CheckResult(
                        type=self.rule_type,
                        name="building_level字段错误",
                        description=f"building_level({equipment_info['building_level']})与设定({building_level})中设定不符",
                        detail=f"building_level({equipment_info['building_level']})与设定({building_level})中设定不符",
                        equipment=[eq],
                        device=device
                    ))

        return results


if __name__ == '__main__':
    pass
