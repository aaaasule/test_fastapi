from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseChangeRule
from app.fid.models import Equipment, CheckResult

class EquipmentDeleteRule(BaseChangeRule):
    rule_name = "设备删除检测"
    rule_type = "warning"
    #在building Level 范围下校验  
    def check(self, current: List[Equipment], previous: List[Equipment], request_data: Dict[str, Any]) -> List[CheckResult]:

        #previous = [p for p in previous if p.building_id == request_data['']]

        previous = previous['building_level']
        curr_ids = {eq.tool_id for eq in current}
        prev_ids = {eq.tool_id for eq in previous}
        results = []

        deleted_tool_id = set([_del.get('code', '') for _del in request_data['delete_equipment_list']])
        print(f"{curr_ids=}")
        for eq in previous:
            if eq.tool_id not in curr_ids and eq.tool_id not in deleted_tool_id and int(eq.is_virtual_eqp) == 0:
                # 删除的设备不在 current 中，但我们可以复制一份用于记录
                deleted_eq = Equipment(
                    tool_id=eq.tool_id,
                    operation="delete"
                )
                results.append(CheckResult(
                    type=self.rule_type,
                    name="设备删除",
                    description="和上一版数据相比设备删除，展示删除设备的TOOL_ID",
                    detail={"TOOL_ID": eq.tool_id},
                    equipment=deleted_eq  # 用于后续提取 operation（虽然 data 中可能不显示删除项）
                ))

                print(f"{eq.tool_id=}")
        return results
