from typing import List, Dict, Any

import sys
from pathlib import Path
from dataclasses import asdict

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseChangeRule
from app.fid.models import Equipment, CheckResult

class UniquenessRule(BaseChangeRule):
    rule_name = "TOOL_ID唯一性校验"
    rule_type = "error"
    #tool id 要在所有设备里校验
    def check(self, current: List[Equipment], previous: List[Equipment], request_data: Dict[str, Any]) -> List[CheckResult]:

        print(f"{previous=}")

        previous = previous['fab']
        previous_tool_ids_same_building = {_p.tool_id:asdict(_p) for _p in previous if (_p.fab_id == request_data['fab']['id']) and \
                                                              (_p.building_id == request_data['building']['id']) and \
                                                              (_p.building_level != request_data['building_level']['code'])}

        previous_tool_ids_diff_building = {_p.tool_id:asdict(_p) for _p in previous if (_p.fab_id == request_data['fab']['id']) and \
                                                              (_p.building_id != request_data['building']['id'])}

        print(f"{request_data=}")
        print(f"{previous_tool_ids_same_building.keys()=}")
        print(f"{previous_tool_ids_diff_building.keys()=}")
        # for _p in previous:
        #     print(f"{_p.tool_id=} {_p.fab_id=} {_p.building_id=} {_p.building_level=} {_p.fab_id == request_data['fab']['id']} {_p.building_id != request_data['building']['id']} or {_p.building_level != request_data['building_level']['code']}")

        results = []
        seen = {}
        eq_map = {}
        for eq in current:
            if eq.tool_id:
                if eq.tool_id in seen:
                    seen[eq.tool_id] += 1
                    eq_map[eq.tool_id].append(eq)
                else:
                    seen[eq.tool_id] = 1
                    eq_map[eq.tool_id] = [eq]

                if eq.tool_id in previous_tool_ids_same_building:
                    results += [CheckResult(
                        type=self.rule_type,
                        name="TOOL_ID不唯一",
                        description="TOOL_ID在厂区内需要保持唯一性",
                        detail={
                            "TOOL_ID": eq.tool_id,
                            "坐标X": eq.insert_point_x,
                            "坐标Y": eq.insert_point_y
                        },
                        equipment=eq)
                    ]
                    print(f"TOOL_ID在FAB内需要保持唯一性{eq.tool_id=}")
                    print(f"{asdict(eq)=}")
                elif eq.tool_id in previous_tool_ids_diff_building:
                    #description = 'TOOL_ID发生迁移:\n'
                    description = ''
                    if eq.building_id != previous_tool_ids_diff_building[eq.tool_id]['building_id']:
                        #description += f"建筑由({eq.building_id})搬到({previous_tool_ids_diff_building[eq.tool_id]['building_id']})\n"
                        description += f"building_id({eq.building_id},{previous_tool_ids_diff_building[eq.tool_id]['building_id']})\n"
                    if eq.building_level != previous_tool_ids_diff_building[eq.tool_id]['building_level']:
                        #description += f"楼层由({eq.building_level})搬到({previous_tool_ids_diff_building[eq.tool_id]['building_level']})\n"
                        description += f"building_level({eq.building_level},{previous_tool_ids_diff_building[eq.tool_id]['building_level']})\n"
                    if eq.grid_x != previous_tool_ids_diff_building[eq.tool_id]['grid_x']:
                        #description += f"柱网X由({eq.grid_x})搬到({previous_tool_ids_diff_building[eq.tool_id]['grid_x']})\n"
                        description += f"grid_x({eq.grid_x},{previous_tool_ids_diff_building[eq.tool_id]['grid_x']})\n"
                    if eq.grid_y != previous_tool_ids_diff_building[eq.tool_id]['grid_y']:
                        #description += f"柱网Y由({eq.grid_y})搬到({previous_tool_ids_diff_building[eq.tool_id]['grid_y']})\n"
                        description += f"grid_y({eq.grid_y},{previous_tool_ids_diff_building[eq.tool_id]['grid_y']})\n"
                    if eq.group_id != previous_tool_ids_diff_building[eq.tool_id]['group_id']:
                        #description += f"组ID由({eq.group_id})搬到({previous_tool_ids_diff_building[eq.tool_id]['group_id']})\n"
                        description += f"group_id({eq.group_id},{previous_tool_ids_diff_building[eq.tool_id]['group_id']})\n"

                    results += [CheckResult(
                        type="warning",
                        name="TOOL_ID不唯一",
                        description=description,
                        detail={
                            "TOOL_ID": eq.tool_id,
                            "坐标X": eq.insert_point_x,
                            "坐标Y": eq.insert_point_y
                        },
                        equipment=eq)
                    ]
                    print(f"TOOL_ID在FAB内发生迁移{eq.tool_id=}")
                    print(f"{asdict(eq)=}")



        for tid in seen:
            print(f"{tid=}")
            if seen[tid] > 1:
                for eq in eq_map[tid]:
                    results += [CheckResult(
                        type=self.rule_type,
                        name="TOOL_ID不唯一",
                        description="TOOL_ID在图纸内需要保持唯一性",
                        detail={
                            "TOOL_ID": tid,
                            "坐标X": eq.insert_point_x,
                            "坐标Y": eq.insert_point_y
                        },
                        equipment=eq)
                    ]
                #]*seen[tid] if seen[tid] > 1 else []

                print(f"tool_id={tid}")


        return results
