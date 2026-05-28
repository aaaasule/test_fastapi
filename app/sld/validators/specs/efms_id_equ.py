"""ID_EQU 须在 EFMS ``equipmentList`` 中存在（按 ``code`` 与图面 ``ID_EQU`` 匹配）。"""
from __future__ import annotations

from typing import List

from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import BaseSpecRule
from app.sld.validators.specs.common import base_detail


class EfmsIdEquRule(BaseSpecRule):
    name = "ID_EQU EFMS 存在性"
    type = "error"
    order = 25

    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        known = ctx.efms_equipment_codes
        if not known:
            return []

        out: List[SldIssue] = []
        for d in devices:
            id_equ = (d.id_equ or "").strip()
            if not id_equ:
                continue
            if id_equ in known:
                continue
            det = base_detail(d)
            det["ID_EQU"] = id_equ
            out.append(
                SldIssue(
                    type="error",
                    name="ID_EQU在EFMS系统中不存在",
                    description=f"ID_EQU={id_equ} 在 EFMS equipmentList 中不存在",
                    detail=det,
                    device=d,
                )
            )
        return out
