"""I_LINE、GPB、母线插板槽等：uniCode 第三段对齐 ID_SHORT，末段对应 EQU.x。"""

from typing import Dict, List, Optional

from . import common
from .match_context import WriteFidMatchContext


def uses_id_short_uni_segment_rule(block_type: str) -> bool:
    if block_type in ("TAKEOFF", "VMB_CHEMICAL", "VMB_GASNAME", "NEW_INTER_"):
        return False
    return True


def match_id_short_family_equipment_code(
    attrs: Dict[str, str],
    interfaces: Optional[List[dict]] = None,
    match_ctx: Optional[WriteFidMatchContext] = None,
) -> str:
    id_short = common.strip(attrs.get("ID_SHORT"))
    if not id_short:
        return ""

    items: List[dict] = []
    if match_ctx is not None:
        items = list(match_ctx.items_by_id_short.get(id_short, []))
    elif interfaces:
        items = interfaces

    for item in items:
        if not common.interface_is_assigned(item):
            continue
        ec = common.strip(item.get("equipmentCode"))
        if not ec:
            continue
        for field in ("uniCode", "code"):
            uc = common.strip(item.get(field))
            if not uc:
                continue
            parts = [p.strip() for p in uc.split(";")]
            if len(parts) < 3:
                continue
            if parts[2] != id_short:
                continue
            last = parts[-1].strip() if parts else ""
            if not last:
                continue
            return ec
    return ""


def id_short_family_equ_suffix_from_item(item: dict) -> str:
    for field in ("uniCode", "code"):
        uc = common.strip(item.get(field))
        if not uc:
            continue
        parts = [p.strip() for p in uc.split(";")]
        if len(parts) < 3:
            continue
        last = parts[-1].strip() if parts else ""
        if last:
            return last
    return ""


def locator_keys_id_short_family(attrs: Dict[str, str]) -> List[str]:
    """
    （已弃用全串匹配）保留供需要旧组合键的场景参考。
    """
    base = common.strip(attrs.get("ID_SHORT"))
    dots = common.id_dot_entries(attrs)
    keys: List[str] = []
    if base:
        keys.append(base)
    for _, vx in dots:
        keys.append(f"{base};{vx}" if base else vx)
    if base and dots:
        joined = ";".join(v for _, v in dots)
        keys.append(f"{base};{joined}")
    return common.dedupe_keys(keys)
