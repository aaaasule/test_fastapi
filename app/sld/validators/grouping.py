"""聚合 SLD 校验问题为 API 分组结构。"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.sld.models import SldIssue


def group_issues(issues: List[SldIssue]) -> List[Dict[str, Any]]:
    """
    将 List[SldIssue] 转为 [{ name, type, description, items: [detail,...] }, ...]
    """
    key_to_items: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    order: List[Tuple[str, str, str]] = []
    for issue in issues:
        key = (issue.name, issue.type, issue.description)
        if key not in key_to_items:
            order.append(key)
        key_to_items[key].append(issue.detail)

    out: List[Dict[str, Any]] = []
    for key in order:
        name, typ, desc = key
        out.append(
            {
                "name": name,
                "type": typ,
                "description": desc,
                "items": key_to_items[key],
            }
        )
    return out
