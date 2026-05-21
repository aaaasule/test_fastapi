"""关键属性缺失（无 tag）+ 必填项空值校验。

两类问题分别归类：
- "关键属性缺失"：ATTRIB tag 完全没有（设备字段为 None）
- "必填项缺失"：tag 存在但值为空字符串
"""
from __future__ import annotations

from typing import List

from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import BaseSpecRule
from app.sld.validators.specs.common import (
    ERROR_KEY_ATTRS,
    WARNING_KEY_ATTRS,
    attr_on_device,
    base_detail,
)


def _collect_missing_and_empty(
    d: SldDevice,
    logical_attrs: tuple[str, ...],
) -> tuple[List[str], List[str]]:
    missing_tags: List[str] = []
    empty_fields: List[str] = []
    for logical in logical_attrs:
        val = attr_on_device(d, logical)
        if val is None:
            missing_tags.append(logical)
        elif isinstance(val, str) and val.strip() == "":
            empty_fields.append(logical)
    return missing_tags, empty_fields


def _append_required_issues(
    out: List[SldIssue],
    d: SldDevice,
    *,
    issue_type: str,
    missing_tags: List[str],
    empty_fields: List[str],
) -> None:
    if missing_tags:
        joined = ", ".join(missing_tags)
        det = base_detail(d)
        det["缺少属性字段"] = joined
        out.append(
            SldIssue(
                type=issue_type,
                name="关键属性缺失",
                description=f"缺少关键业务属性：{joined}",
                detail=det,
                device=d,
            )
        )
    if empty_fields:
        joined = ", ".join(empty_fields)
        det2 = base_detail(d)
        det2["未填写字段"] = joined
        out.append(
            SldIssue(
                type=issue_type,
                name="必填项缺失",
                description=f"必填项未填写：{joined}",
                detail=det2,
                device=d,
            )
        )


class RequiredRule(BaseSpecRule):
    name = "关键属性必填"
    type = "error"
    order = 40

    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        out: List[SldIssue] = []
        for d in devices:
            error_missing, error_empty = _collect_missing_and_empty(d, ERROR_KEY_ATTRS)
            warning_missing, warning_empty = _collect_missing_and_empty(d, WARNING_KEY_ATTRS)
            _append_required_issues(
                out,
                d,
                issue_type="error",
                missing_tags=error_missing,
                empty_fields=error_empty,
            )
            _append_required_issues(
                out,
                d,
                issue_type="warning",
                missing_tags=warning_missing,
                empty_fields=warning_empty,
            )
        return out
