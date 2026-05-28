"""设备属性修改校验：同业务键比对 OWNER（图面）/ groupCode（历史）/ VENDOR / MODEL / BAY_LOCATION。"""
from __future__ import annotations

from typing import List, Tuple

from app.sld.models import SldDevice, SldIssue
from app.sld.validators.changes.base import BaseChangeRule
from app.sld.validators.changes.common import HistoryIndex, hist_device_dict
from app.sld.validators.specs.common import business_key

_FIELDS: Tuple[Tuple[str, str, str], ...] = (
    # (设备字段名, 历史 dict 字段名, 展示用 label)
    ("owner", "group_code", "OWNER"),
    ("vendor", "vendor", "VENDOR"),
    ("model", "model", "MODEL"),
    ("bay_location", "bay_location", "BAY_LOCATION"),
)


class AttributeModifiedRule(BaseChangeRule):
    name = "设备属性修改"
    type = "warning"
    order = 130

    def check(
        self,
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        issues: List[SldIssue] = []
        for d in current:
            k = business_key(d)
            if not k.strip("+") or k not in history.by_biz:
                continue
            h = hist_device_dict(history.by_biz[k])
            for attr, h_key, label in _FIELDS:
                curr_val = (getattr(d, attr) or "").strip()
                prev_val = h[h_key]
                if curr_val == prev_val:
                    continue
                d.operation = "update"
                issues.append(
                    SldIssue(
                        type="warning",
                        name="设备属性修改",
                        description="同样ID_EQU+ID_EquSubShort设备和上一版相比属性修改",
                        detail={
                            "ID_EQU+ID_EquSubShort": k,
                            "属性字段": label,
                            "FROM": prev_val,
                            "TO": curr_val,
                            "坐标X": d.center_point_x,
                            "坐标Y": d.center_point_y,
                        },
                        device=d,
                    )
                )
        return issues
