"""设备新增校验：当前业务键 - 历史业务键。"""
from __future__ import annotations

from typing import List

from app.sld.models import SldDevice, SldIssue
from app.sld.validators.changes.base import BaseChangeRule
from app.sld.validators.changes.common import HistoryIndex
from app.sld.validators.specs.common import business_key


class AddedRule(BaseChangeRule):
    name = "设备新增"
    type = "warning"
    order = 110

    def check(
        self,
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        issues: List[SldIssue] = []
        hist_keys = set(history.by_biz.keys())
        for d in current:
            k = business_key(d)
            if not k.strip("+") or k == "+":
                continue
            if k in hist_keys:
                continue
            d.operation = "add"
            issues.append(
                SldIssue(
                    type="warning",
                    name="设备新增",
                    description="和上一版数据相比设备新增",
                    detail={
                        "ID_EQU+ID_EquSubShort": k,
                        "坐标X": d.center_point_x,
                        "坐标Y": d.center_point_y,
                    },
                    device=d,
                )
            )
        return issues
