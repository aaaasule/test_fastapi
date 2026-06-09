"""SLD API 输出格式化工具。"""
from __future__ import annotations

from typing import Any


def clearable_str(value: Any) -> str:
    """图面可为空的字符串字段：输出 ``""`` 而非 ``null``，便于 EFMS 持久化「清空」。"""
    if value is None:
        return ""
    return str(value).strip()
