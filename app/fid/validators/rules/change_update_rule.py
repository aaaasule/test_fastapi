from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseChangeRule
from app.fid.models import Equipment, CheckResult


class EquipmentUpdateRule(BaseChangeRule):
    rule_name = "设备修改检测"
    rule_type = "warning"

    def check(self, current: List[Equipment], previous: List[Equipment], request_data: Dict[str, Any]) -> List[
        CheckResult]:

        previous = previous['building_level']
        curr_map = {eq.tool_id: eq for eq in current}
        prev_map = {eq.tool_id: eq for eq in previous}
        results = []
        threshold = 0.1

        for tid in curr_map.keys() & prev_map.keys():
            curr_eq = curr_map[tid]
            prev_eq = prev_map[tid]

            description = ""
            for attr in ["group_id", "model", "bay_location"]:
                curr_value = getattr(curr_eq, attr)
                prev_value = getattr(prev_eq, attr)

                # if curr_value not in ['', None] and prev_value not in ['', None] and  != getattr(prev_eq, attr):
                if curr_value != prev_value:
                    # if curr_eq.get(attr, '') != prev_eq.get(attr, ''):

                    if prev_value not in ['', None] or curr_value not in ['', None]:
                        description += f"{attr}({getattr(prev_eq, attr)},{getattr(curr_eq, attr)})\n"

                        # #后端要自己校验变更内容，不会获取返回的description，直接break即可
                        # break

            if len(description) > 0:
                curr_eq.operation = "update"  # ✅ 标记为修改
                results.append(CheckResult(
                    type=self.rule_type,
                    name="设备属性修改",
                    description=description,
                    detail={"TOOL_ID": tid, "属性字段": attr, "FROM": getattr(prev_eq, attr),
                            "TO": getattr(curr_eq, attr),
                            "坐标X": curr_eq.insert_point_x, "坐标Y": curr_eq.insert_point_y},
                    equipment=curr_eq
                ))

            # 检查位置变更
            location_description = ""
            try:
                dx = abs(curr_eq.insert_point_x - prev_eq.insert_point_x)
                dy = abs(curr_eq.insert_point_y - prev_eq.insert_point_y)
                dz = abs(curr_eq.insert_point_z - prev_eq.insert_point_z)

                # if dx >= threshold or dy >= threshold or dz >= threshold:
                #     curr_eq.operation = "update"
                #     results.append(CheckResult(
                #         type=self.rule_type,
                #         name="设备位置变更",
                #         description=f"同样TOOL_ID设备和上一版数据相比设备位置变更 {dx=} {dy=} {dz=}",
                #         detail={"TOOL_ID": tid, "FROM": f"X: {prev_eq.insert_point_x}, Y: {prev_eq.insert_point_y}",
                #                 "TO": f"X: {curr_eq.insert_point_x}, Y: {curr_eq.insert_point_y}",
                #                 "坐标X": curr_eq.insert_point_x, "坐标Y": curr_eq.insert_point_y},
                #         equipment=curr_eq
                #     ))

                if dx >= threshold:
                    location_description += f"insert_point_x({curr_eq.insert_point_x},{prev_eq.insert_point_x})\n"
                if dy >= threshold:
                    location_description += f"insert_point_y({curr_eq.insert_point_y},{prev_eq.insert_point_y})\n"
                if dz >= threshold:
                    location_description += f"insert_point_z({curr_eq.insert_point_z},{prev_eq.insert_point_z})\n"
                if len(location_description) > 0:
                    curr_eq.operation = "update"
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="设备位置变更",
                        description=location_description,
                        detail={"TOOL_ID": tid, "FROM": f"X: {prev_eq.insert_point_x}, Y: {prev_eq.insert_point_y}",
                                "TO": f"X: {curr_eq.insert_point_x}, Y: {curr_eq.insert_point_y}",
                                "坐标X": curr_eq.insert_point_x, "坐标Y": curr_eq.insert_point_y},
                        equipment=curr_eq
                    ))
                    print(f"{tid=}")
                    print(f"{dx=}")
                    print(f"{dy=}")
                    print(f"{dz=}")
            except:
                # if (str(curr_eq.insert_point_x) != str(prev_eq.insert_point_x)) or \
                # (str(curr_eq.insert_point_y) != str(prev_eq.insert_point_y)) or \
                # (str(curr_eq.insert_point_z) != str(prev_eq.insert_point_z)):
                if str(curr_eq.insert_point_x) != str(prev_eq.insert_point_x):
                    location_description += f"insert_point_x({curr_eq.insert_point_x},{prev_eq.insert_point_x})\n"
                if str(curr_eq.insert_point_y) != str(prev_eq.insert_point_y):
                    location_description += f"insert_point_y({curr_eq.insert_point_y},{prev_eq.insert_point_y})\n"
                if str(curr_eq.insert_point_z) != str(prev_eq.insert_point_z):
                    location_description += f"insert_point_z({curr_eq.insert_point_z},{prev_eq.insert_point_z})\n"

                if len(location_description) > 0:
                    curr_eq.operation = "update"
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="设备位置变更",
                        description=f"同样TOOL_ID设备和上一版数据相比设备位置变更",
                        detail={"TOOL_ID": tid, "FROM": f"X: {prev_eq.insert_point_x}, Y: {prev_eq.insert_point_y}",
                                "TO": f"X: {curr_eq.insert_point_x}, Y: {curr_eq.insert_point_y}",
                                "坐标X": curr_eq.insert_point_x, "坐标Y": curr_eq.insert_point_y},
                        equipment=curr_eq
                    ))
                    print(f"{curr_eq.insert_point_x=} {prev_eq.insert_point_x=}")
                    print(f"{curr_eq.insert_point_y=} {prev_eq.insert_point_y=}")
                    print(f"{curr_eq.insert_point_z=} {prev_eq.insert_point_z=}")
        return results
