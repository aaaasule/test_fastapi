"""文件名规范性校验：``stem == "<company>^SLD^<building>^<level>"``。"""
from __future__ import annotations

from typing import List

from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import BaseSpecRule


class FilenameRule(BaseSpecRule):
    name = "文件名格式"
    type = "error"
    order = 10
    enabled = False

    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        stem = ctx.filename_stem
        expected = f"{ctx.company_token}^SLD^{ctx.building_token}^{ctx.level_token}"
        if stem == expected:
            return []
        return [
            SldIssue(
                type="error",
                name="文件名格式错误",
                description=f"格式应为 {expected}",
                detail={"filename": stem, "expected": expected},
                device=devices[0] if devices else None,
            )
        ]
