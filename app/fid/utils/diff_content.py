import re
from typing import Any, List

_DIFF_ITEM_PATTERN = re.compile(r"([^\s,(]+)\(([^,]*),([^)]*)\)")


def format_diff_item(attr: str, old_value: Any, new_value: Any) -> str:
    """格式：属性名（旧值，新值）"""
    return f"{attr}（{old_value}，{new_value}）"


NOT_EXISTING_RESTORE_DIFF_ITEM = "status(not_existing_in_fid,update)"
NOT_EXISTING_IN_ELD_STATUS = "not_existing_in_eld"


def build_not_existing_restore_diff_item(old_status: str, new_status: str = "update") -> str:
    """构造 status 恢复类 diff 项，格式：status(旧值,新值)。"""
    return f"status({old_status},{new_status})"


def build_not_existing_restore_detail(summary: str) -> dict:
    """图面重新出现、但后端曾标记 not_existing_in_fid 时的 diff 详情。"""
    return {
        "summary": summary,
        "diff_items": [NOT_EXISTING_RESTORE_DIFF_ITEM],
    }


def build_eld_not_existing_restore_detail(summary: str, old_status: str) -> dict:
    """图面重新出现、但后端曾标记 not_existing_in_eld（或其它 not_* status）时的 diff 详情。"""
    return {
        "summary": summary,
        "diff_items": [build_not_existing_restore_diff_item(old_status)],
    }


def normalize_diff_item(item: str) -> str:
    text = (item or "").strip()
    if not text:
        return ""
    if "（" in text and "）" in text:
        return text

    match = _DIFF_ITEM_PATTERN.fullmatch(text) or _DIFF_ITEM_PATTERN.search(text)
    if match:
        return format_diff_item(match.group(1), match.group(2), match.group(3))
    return text


def extract_diff_items_from_text(text: str) -> List[str]:
    if not text:
        return []

    items: List[str] = []
    seen = set()
    for match in _DIFF_ITEM_PATTERN.finditer(text):
        formatted = format_diff_item(match.group(1), match.group(2), match.group(3))
        if formatted not in seen:
            seen.add(formatted)
            items.append(formatted)
    return items


def build_fid_diff_content(warning_data) -> List[str]:
    """从 FID 变更校验结果构造 diffContent 列表。"""
    detail = getattr(warning_data, "detail", None)

    if isinstance(detail, dict):
        diff_items = detail.get("diff_items")
        if isinstance(diff_items, list):
            result: List[str] = []
            seen = set()
            for item in diff_items:
                normalized = normalize_diff_item(str(item))
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    result.append(normalized)
            if result:
                return result

        for key in ("summary", "text"):
            parsed = extract_diff_items_from_text(str(detail.get(key) or ""))
            if parsed:
                return parsed

    if isinstance(detail, str):
        parsed = extract_diff_items_from_text(detail)
        if parsed:
            return parsed

    description = getattr(warning_data, "description", "") or ""
    return extract_diff_items_from_text(description)
