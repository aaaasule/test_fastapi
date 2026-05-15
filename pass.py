def interface_is_assigned(item: dict) -> bool:
    """已派点：isAssigned 不为 3（仅 3 视为未派点）；缺省/非数字按已派点处理。"""
    v = item.get("isAssigned")
    if v is None:
        return True
    try:
        return int(v) != 3
    except (TypeError, ValueError):
        return True
