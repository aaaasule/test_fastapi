from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseChangeRule
from app.fid.models import Equipment, CheckResult

_ATTR_LABELS = {
    "group_id": "OWNER",
    "model": "MODEL",
    "bay_location": "BAY_LOCATION",
    "insert_point_x": "INSERT_POINT_X",
    "insert_point_y": "INSERT_POINT_Y",
    "insert_point_z": "INSERT_POINT_Z",
}


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
            diff_items = []
            for attr in ["group_id", "model", "bay_location"]:
                curr_value = getattr(curr_eq, attr)
                prev_value = getattr(prev_eq, attr)

                # if curr_value not in ['', None] and prev_value not in ['', None] and  != getattr(prev_eq, attr):
                if curr_value != prev_value:
                    # if curr_eq.get(attr, '') != prev_eq.get(attr, ''):

                    if prev_value not in ['', None] or curr_value not in ['', None]:
                        label = _ATTR_LABELS.get(attr, attr)
                        change_text = f"{label}({getattr(prev_eq, attr)},{getattr(curr_eq, attr)})"
                        description += change_text + "\n"
                        diff_items.append(change_text)

                        # #后端要自己校验变更内容，不会获取返回的description，直接break即可
                        # break

            if len(description) > 0:
                curr_eq.operation = "update"  # ✅ 标记为修改
                results.append(CheckResult(
                    type=self.rule_type,
                    name="设备属性修改",
                    description=description,
                    detail={
                        "TOOL_ID": tid,
                        "diff_items": diff_items,
                        "坐标X": curr_eq.insert_point_x,
                        "坐标Y": curr_eq.insert_point_y,
                    },
                    equipment=curr_eq
                ))

            # 检查位置变更
            location_description = ""
            location_diff_items = []
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
                    label = _ATTR_LABELS.get("insert_point_x", "insert_point_x")
                    change_text = f"{label}({prev_eq.insert_point_x},{curr_eq.insert_point_x})"
                    location_description += change_text + "\n"
                    location_diff_items.append(change_text)
                if dy >= threshold:
                    label = _ATTR_LABELS.get("insert_point_y", "insert_point_y")
                    change_text = f"{label}({prev_eq.insert_point_y},{curr_eq.insert_point_y})"
                    location_description += change_text + "\n"
                    location_diff_items.append(change_text)
                if dz >= threshold:
                    label = _ATTR_LABELS.get("insert_point_z", "insert_point_z")
                    change_text = f"{label}({prev_eq.insert_point_z},{curr_eq.insert_point_z})"
                    location_description += change_text + "\n"
                    location_diff_items.append(change_text)
                if len(location_description) > 0:
                    curr_eq.operation = "update"
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="设备位置变更",
                        description=location_description,
                        detail={
                            "TOOL_ID": tid,
                            "diff_items": location_diff_items,
                            "坐标X": curr_eq.insert_point_x,
                            "坐标Y": curr_eq.insert_point_y,
                        },
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
                    label = _ATTR_LABELS.get("insert_point_x", "insert_point_x")
                    change_text = f"{label}({prev_eq.insert_point_x},{curr_eq.insert_point_x})"
                    location_description += change_text + "\n"
                    location_diff_items.append(change_text)
                if str(curr_eq.insert_point_y) != str(prev_eq.insert_point_y):
                    label = _ATTR_LABELS.get("insert_point_y", "insert_point_y")
                    change_text = f"{label}({prev_eq.insert_point_y},{curr_eq.insert_point_y})"
                    location_description += change_text + "\n"
                    location_diff_items.append(change_text)
                if str(curr_eq.insert_point_z) != str(prev_eq.insert_point_z):
                    label = _ATTR_LABELS.get("insert_point_z", "insert_point_z")
                    change_text = f"{label}({prev_eq.insert_point_z},{curr_eq.insert_point_z})"
                    location_description += change_text + "\n"
                    location_diff_items.append(change_text)

                if len(location_description) > 0:
                    curr_eq.operation = "update"
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="设备位置变更",
                        description=location_description,
                        detail={
                            "TOOL_ID": tid,
                            "diff_items": location_diff_items,
                            "坐标X": curr_eq.insert_point_x,
                            "坐标Y": curr_eq.insert_point_y,
                        },
                        equipment=curr_eq
                    ))
                    print(f"{curr_eq.insert_point_x=} {prev_eq.insert_point_x=}")
                    print(f"{curr_eq.insert_point_y=} {prev_eq.insert_point_y=}")
                    print(f"{curr_eq.insert_point_z=} {prev_eq.insert_point_z=}")
        return results
