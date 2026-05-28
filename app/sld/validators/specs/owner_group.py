"""设备 OWNER 编组校验：必须落在请求 ``equipmentGroupList`` 允许的 Equipment Group 范围内。"""
from __future__ import annotations

from typing import List

from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import BaseSpecRule
from app.sld.validators.specs.common import base_detail


class OwnerGroupRule(BaseSpecRule):
    name = "OWNER 编组"
    type = "warning"
    order = 50

    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        allowed = ctx.allowed_owner_codes
        if not allowed:
            return []
        out: List[SldIssue] = []
        for d in devices:
            owner = (d.owner or "").strip().upper()
            if not owner:
                continue
            if owner in allowed:
                continue
            det = base_detail(d)
            det["OWNER"] = d.owner
            out.append(
                SldIssue(
                    type="warning",
                    name="设备编组错误",
                    description="OWNER字段不在允许的Equipment group范围内",
                    detail=det,
                    device=d,
                )
            )
        return out
