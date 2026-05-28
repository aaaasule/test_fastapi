"""ID_EQU+ID_EquSubShort 全局唯一性校验。"""
from __future__ import annotations

from typing import Dict, List

from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import BaseSpecRule
from app.sld.validators.specs.common import business_key


class UniquenessRule(BaseSpecRule):
    name = "业务键唯一性"
    type = "error"
    order = 30

    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        by_key: Dict[str, List[SldDevice]] = {}
        for d in devices:
            k = business_key(d)
            if not k.strip("+") or k == "+":
                continue
            by_key.setdefault(k, []).append(d)

        issues: List[SldIssue] = []
        for k, group in by_key.items():
            if len(group) < 2:
                continue
            coords = [
                {"X": x.center_point_x, "Y": x.center_point_y, "block_id": x.block_id}
                for x in group
            ]
            dup_detail = {"ID_EQU+ID_EquSubShort": k, "occurrences": coords}
            for d in group:
                issues.append(
                    SldIssue(
                        type="error",
                        name="ID_EQU+ID_EquSubShort不唯一",
                        description=(
                            f"ID_EQU={d.id_equ or ''}, "
                            f"ID_EquSubShort={d.id_equ_sub_short or ''}，需保持唯一性"
                        ),
                        detail=dup_detail,
                        device=d,
                    )
                )
        return issues
