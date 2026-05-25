"""I_LINE、GPB、母线插板槽等：uniCode 第三段对齐 ID_SHORT，末段对应 EQU.x。"""

from typing import Dict, List, Optional, Set

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


def id_short_port_values(attrs: Dict[str, str]) -> Set[str]:
    """图块上 ID.xx 取值及标签后缀，用于与 uniCode 末段对齐。"""
    ports: Set[str] = set()
    for id_tag, val in common.id_dot_entries(attrs):
        v = common.strip(val)
        if v:
            ports.add(v)
        if len(id_tag) > 3:
            suf = common.strip(id_tag[3:])
            if suf:
                ports.add(suf)
                if suf.isdigit():
                    ports.add(str(int(suf)))
    return ports


def id_short_item_matches_insert(attrs: Dict[str, str], item: dict) -> bool:
    """ID_SHORT 族：uniCode 第 3 段=ID_SHORT，末段落在图块 ID.xx 端口集合内。"""
    if not common.parent_line_effective_assigned(item):
        return False
    if not common.strip(item.get("equipmentCode")):
        return False
    id_short = common.strip(attrs.get("ID_SHORT"))
    if not id_short:
        return False
    last = id_short_family_equ_suffix_from_item(item)
    if not last:
        return False
    port_vals = id_short_port_values(attrs)
    if not last in port_vals:
        return False
    for field in ("uniCode", "code"):
        uc = common.strip(item.get(field))
        if not uc:
            continue
        parts = [p.strip() for p in uc.split(";")]
        if len(parts) >= 3 and parts[2] == id_short:
            return True
    return False


def find_id_short_matched_interfaces(
    insert_attrs: Dict[str, str],
    interfaces: Optional[List[dict]] = None,
    match_ctx: Optional[WriteFidMatchContext] = None,
) -> List[dict]:
    """同一 INSERT 下按 ID_SHORT + 各端口末段关联多条入参接口。"""
    id_short = common.strip(insert_attrs.get("ID_SHORT"))
    if not id_short or not id_short_port_values(insert_attrs):
        return []

    if match_ctx is not None:
        candidates = list(match_ctx.items_by_id_short.get(id_short, []))
    elif interfaces:
        candidates = []
        for item in interfaces:
            if not common.parent_line_effective_assigned(item):
                continue
            if not common.strip(item.get("equipmentCode")):
                continue
            for field in ("uniCode", "code"):
                uc = common.strip(item.get(field))
                if not uc:
                    continue
                parts = [p.strip() for p in uc.split(";")]
                if len(parts) >= 3 and parts[2] == id_short:
                    candidates.append(item)
                    break
    else:
        return []

    matched: List[dict] = []
    seen_ids: set = set()
    for item in candidates:
        if not id_short_item_matches_insert(insert_attrs, item):
            continue
        item_id = item.get("id")
        dedupe_key = item_id if item_id is not None else id(item)
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        matched.append(item)
    return matched


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
