from typing import List, Dict, Any

import sys
from pathlib import Path
from dataclasses import asdict

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseChangeRule
from app.fid.models import Equipment, CheckResult

class EquipmentAddRule(BaseChangeRule):
    rule_name = "设备新增检测"
    rule_type = "warning"
    #在building Level 范围下校验  
    def check(self, current: List[Equipment], previous: List[Equipment], request_data: Dict[str, Any]) -> List[CheckResult]:

        # previous = previous['fab']
        # curr_ids = {eq.tool_id for eq in current}
        # prev_ids = set()
        # virtual_status_dict = {}
        # for eq in previous:
        #     if eq.tool_id not in prev_ids:
        #         prev_ids.add(eq.tool_id)
        #     if eq.tool_id not in virtual_status_dict:
        #         virtual_status_dict[eq.tool_id] = int(eq.is_virtual_eqp)
        #
        #
        # results = []
        #
        # deleted_tool_id = request_data['delete_equipment_list']
        #
        # print(f"{prev_ids=}")
        # for eq in current:
        #
        #     if eq.tool_id not in prev_ids:
        #
        #         if eq.tool_id not in deleted_tool_id:
        #             # ✅ 标记为新增
        #             eq.operation = "add"
        #
        #             results.append(CheckResult(
        #                 type=self.rule_type,
        #                 name="设备新增",
        #                 description="和上一版数据相比设备新增，展示新增设备的TOOL_ID",
        #                 detail={
        #                     "TOOL_ID": eq.tool_id,
        #                     "坐标X": eq.insert_point_x,
        #                     "坐标Y": eq.insert_point_y
        #                 },
        #                 equipment=eq
        #             ))
        #         else:
        #             # ✅ 标记为更新
        #             eq.operation = "update"
        #
        #             results.append(CheckResult(
        #                 type="warning",
        #                 name="设备新增",
        #                 description="和上一版数据相比设备新增，展示新增设备的TOOL_ID",
        #                 detail={
        #                     "TOOL_ID": eq.tool_id,
        #                     "坐标X": eq.insert_point_x,
        #                     "坐标Y": eq.insert_point_y
        #                 },
        #                 equipment=eq
        #             ))
        #
        #
        #         print(f"{eq.tool_id=}")
        #     else:
        #         # 虚拟设备认为是update
        #         if virtual_status_dict.get(eq.tool_id) == 1:
        #             eq.operation = "update"
        #
        #             results.append(CheckResult(
        #                 type=self.rule_type,
        #                 name="设备新增",
        #                 description="和上一版数据相比，虚拟设备新增，展示虚拟设备的TOOL_ID",
        #                 detail={
        #                     "TOOL_ID": eq.tool_id,
        #                     "坐标X": eq.insert_point_x,
        #                     "坐标Y": eq.insert_point_y
        #                 },
        #                 equipment=eq
        #             ))
        #
        #             eq.is_virtual_eqp = 0
        # return results

        #0401 update
        previous = previous['fab']

        prev_ids = set()

        virtual_status_dict = {}
        for eq in previous:
            if eq.tool_id not in prev_ids:
                prev_ids.add(eq.tool_id)
            if eq.tool_id not in virtual_status_dict:
                virtual_status_dict[eq.tool_id] = int(eq.is_virtual_eqp)


        results = []

        deleted_tool_id = [_del.get('code','') for _del in request_data['delete_equipment_list']]

        for eq in current:

            if eq.tool_id not in prev_ids:
                # ✅ 标记为新增
                eq.operation = "add"

                results.append(CheckResult(
                    type=self.rule_type,
                    name="设备新增",
                    description="和上一版数据相比设备新增，展示新增设备的TOOL_ID",
                    detail={
                        "TOOL_ID": eq.tool_id,
                        "坐标X": eq.insert_point_x,
                        "坐标Y": eq.insert_point_y
                    },
                    equipment=eq
                ))

            else:

                description = ''
                # 虚拟设备认为是update
                if virtual_status_dict.get(eq.tool_id) == 1:
                    eq.operation = "update"
                    description+="和上一版数据相比，虚拟设备新增，展示虚拟设备的TOOL_ID\n"
                    eq.is_virtual_eqp = 0

                # 删除重新加回来
                if eq.tool_id in deleted_tool_id:
                    # ✅ 标记为更新
                    eq.operation = "update"
                    description += "和上一版数据相比设备新增，展示新增设备的TOOL_ID\n"

                if len(description) > 0:
                    results.append(CheckResult(
                        type="warning",
                        name="设备新增",
                        description=description,
                        detail={
                            "TOOL_ID": eq.tool_id,
                            "坐标X": eq.insert_point_x,
                            "坐标Y": eq.insert_point_y
                        },
                        equipment=eq
                    ))


            print(f"{eq.tool_id=}")
        return results
