"""设备位置变更校验：

1. 同业务键(ID_EQU+ID_EquSubShort)：比对中心点欧氏距离。
2. TOOL_ID 兜底：业务键不命中、但 TOOL_ID 命中时再查一次，避免漏检。

命中即把 ``d.operation`` 标记为 ``"update"``。
"""
from __future__ import annotations

import math
from typing import List

from app.sld.constants import POSITION_CHANGE_EPSILON
from app.sld.models import SldDevice, SldIssue
from app.sld.validators.changes.base import BaseChangeRule
from app.sld.validators.changes.common import HistoryIndex, hist_device_dict, hist_float
from app.sld.validators.specs.common import business_key


class PositionChangedRule(BaseChangeRule):
    name = "设备位置变更"
    type = "warning"
    order = 140

    def check(
        self,
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        issues: List[SldIssue] = []
        issues.extend(self._check_by_biz_key(current, history))
        issues.extend(self._check_by_tool_id(current, history))
        return issues

    @staticmethod
    def _check_by_biz_key(
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        issues: List[SldIssue] = []
        for d in current:
            k = business_key(d)
            if not k.strip("+") or k not in history.by_biz:
                continue
            h = hist_device_dict(history.by_biz[k])
            dist = math.hypot(d.center_point_x - h["center_x"], d.center_point_y - h["center_y"])
            if dist <= POSITION_CHANGE_EPSILON:
                continue
            d.operation = "update"
            issues.append(
                SldIssue(
                    type="warning",
                    name="设备位置变更",
                    description="同样业务键设备上一版与当前中心点不一致",
                    detail={
                        "ID_EQU+ID_EquSubShort": k,
                        "FROM": f"X: {h['center_x']}, Y: {h['center_y']}",
                        "TO": f"X: {d.center_point_x}, Y: {d.center_point_y}",
                        "坐标X": d.center_point_x,
                        "坐标Y": d.center_point_y,
                    },
                    device=d,
                )
            )
        return issues

    @staticmethod
    def _check_by_tool_id(
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        issues: List[SldIssue] = []
        for d in current:
            tid = (d.tool_id or "").strip()
            if not tid or tid not in history.by_tool:
                continue
            # 业务键能命中的已经在 _check_by_biz_key 处理过
            if business_key(d) in history.by_biz:
                continue
            hitem = history.by_tool[tid]
            hx = hist_float(hitem, "centerPointX", "center_point_x")
            hy = hist_float(hitem, "centerPointY", "center_point_y")
            dist = math.hypot(d.center_point_x - hx, d.center_point_y - hy)
            if dist <= POSITION_CHANGE_EPSILON:
                continue
            d.operation = "update"
            issues.append(
                SldIssue(
                    type="warning",
                    name="设备位置变更(TOOL_ID)",
                    description="同样TOOL_ID设备和上一版相比设备位置变更",
                    detail={
                        "TOOL_ID": tid,
                        "FROM": f"X: {hx}, Y: {hy}",
                        "TO": f"X: {d.center_point_x}, Y: {d.center_point_y}",
                        "坐标X": d.center_point_x,
                        "坐标Y": d.center_point_y,
                    },
                    device=d,
                )
            )
        return issues
