"""ID_EQU 命名规范性校验：匹配 ``ID_EQU_PATTERN`` 正则。"""
from __future__ import annotations

import re
from typing import List

from app.sld.constants import ID_EQU_PATTERN
from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import BaseSpecRule
from app.sld.validators.specs.common import base_detail


class IdEquFormatRule(BaseSpecRule):
    name = "ID_EQU 规范性"
    type = "error"
    order = 20
    enabled = False  # False 规则不校验

    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        pat = re.compile(ID_EQU_PATTERN)
        out: List[SldIssue] = []
        for d in devices:
            v = (d.id_equ or "").strip()
            if not v:
                continue
            if pat.match(v):
                continue
            det = base_detail(d)
            det["CAD编码"] = d.block_name
            out.append(
                SldIssue(
                    type="error",
                    name="ID_EQU规范性错误",
                    description="设备命名应以大写字母开头，（只允许'-'）",
                    detail=det,
                    device=d,
                )
            )
        return out
