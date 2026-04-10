# validators/rules/grid_pillar_match_rule.py
from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseSearchRule
from app.fid.models import Equipment, CheckResult

class GridPillarMatchRule(BaseSearchRule):
    rule_name = "柱网匹配校验"
    rule_type = "warning"

    def __init__(self, grid_pillar_finder=None):
        self.finder = grid_pillar_finder

    def check(self, equipments: List[Equipment], check_info: Any) -> List[CheckResult]:
        if not self.finder:
            return []

        # 构造 (tool_id, x, y) 列表
        devices_with_id = [
            (eq.tool_id, eq.center_point_x, eq.center_point_y)
            for eq in equipments
        ]

        # 执行匹配
        match_results = self.finder.find_nearest_for_devices(devices_with_id)

        check_results = []

        for eq, res in zip(equipments, match_results):
            # 设置 bay_location 为柱子名称
            #eq.nearest_pillar_name = res["nearest_pillar_name"]
            (eq.nearest_pillar_x, eq.nearest_pillar_y) = res["nearest_pillar_coord"]
            eq.device_coord = res["device_coord"]
            eq.distance = res["distance"]
            (eq.grid_x, eq.grid_y) = res["nearest_pillar_name"]

        return check_results
