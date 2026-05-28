"""VMB / Slurry：equipmentCode 写入与 ID.x 对应的 EQU.x，无 ID.x 时兜底。"""

from typing import Dict, List, Optional, Set

from . import common


def _normalize_code(value: str) -> str:
    return str(value or "").strip()


def _get_last_segment(value: str) -> str:
    code = _normalize_code(value)
    if not code:
        return ""
    return code.split(";")[-1].strip()


def infer_id_suffix_from_code(interface_code: str) -> str:
    tail = _get_last_segment(interface_code)
    if not tail:
        return ""
    if "-" in tail:
        return tail.rsplit("-", 1)[-1].strip()
    return tail


def equipment_for_takeoff_branch(branch_map: Dict[str, str], port_label: str) -> str:
    """
    takeoff_group_map 分支键（如 12-S2）与图块端口标注（如 S2）对齐后取 equipmentCode。
    """
    port_label = str(port_label or "").strip()
    if not port_label or not branch_map:
        return ""
    if port_label in branch_map:
        return _normalize_code(branch_map[port_label])
    for branch_key in sorted(branch_map.keys()):
        bk = str(branch_key or "").strip()
        if not bk:
            continue
        tail = bk.split("-")[-1].strip()
        if tail == port_label:
            return _normalize_code(branch_map[branch_key])
    return ""


def _matched_locator_codes_casefold(item: Optional[dict]) -> Set[str]:
    """与 locator_keys_vmb_slurry 一致的完整定位串（uniCode / code），用于多端口块只回填命中端口。"""
    if not item:
        return set()
    out: Set[str] = set()
    for field in ("uniCode", "code"):
        v = common.strip(item.get(field))
        if v:
            out.add(v.casefold())
    return out


def _matched_locator_codes_casefold_from_items(items: Optional[List[dict]]) -> Set[str]:
    """同一 INSERT 多条匹配接口时，并集所有允许写入的定位串。"""
    out: Set[str] = set()
    if not items:
        return out
    for item in items:
        out |= _matched_locator_codes_casefold(item)
    return out


def _equipment_for_vmb_port(
    compound: str,
    matched_items: List[dict],
    equipment_code: str,
) -> str:
    """按端口复合键命中对应接口行的 equipmentCode，否则用聚合值兜底。"""
    cf = compound.casefold()
    for item in matched_items:
        for field in ("uniCode", "code"):
            v = common.strip(item.get(field))
            if v and v.casefold() == cf:
                ec = _normalize_code(item.get("equipmentCode"))
                if ec:
                    return ec
    return _normalize_code(equipment_code)


from .match_vmb import vmb_compound_locator_key as _vmb_compound_locator_key


def write_vmb_slurry_equipment_code(
    attrs_plain: Dict[str, str],
    attrs_by_tag: dict,
    equipment_code: str,
    interface_code: str,
    id_code: str,
    takeoff_branch_map: Optional[Dict[str, str]] = None,
    matched_item: Optional[dict] = None,
    matched_items: Optional[List[dict]] = None,
) -> bool:
    dots = common.id_dot_entries(attrs_plain)
    wrote = False
    items_for_match = matched_items or (
        [matched_item] if matched_item is not None else []
    )
    matched_loc_cf = _matched_locator_codes_casefold_from_items(items_for_match)
    restrict_to_assigned_port = bool(matched_loc_cf) and takeoff_branch_map is None
    id_main = common.strip(attrs_plain.get("ID"))
    if dots:
        for id_tag, vid_val in dots:
            if not id_tag.startswith("ID.") or len(id_tag) < 4:
                continue
            suf = id_tag[3:].strip()
            if not suf:
                continue
            equ_dot_tag = f"EQU.{suf.upper()}"
            target_attr = attrs_by_tag.get(equ_dot_tag)
            if target_attr is None:
                continue
            vx = common.strip(vid_val)
            if not vx:
                continue
            compound = _vmb_compound_locator_key(id_main, vx)
            if restrict_to_assigned_port and compound.casefold() not in matched_loc_cf:
                continue
            if takeoff_branch_map:
                code = equipment_for_takeoff_branch(takeoff_branch_map, vid_val)
                if not code:
                    continue
            elif items_for_match:
                code = _equipment_for_vmb_port(compound, items_for_match, equipment_code)
            else:
                code = _normalize_code(equipment_code)
            if code:
                target_attr.dxf.text = code
                wrote = True
    else:
        suffix = infer_id_suffix_from_code(interface_code or id_code)
        if suffix:
            equ_dot_tag = f"EQU.{suffix.upper()}"
            target_attr = attrs_by_tag.get(equ_dot_tag)
            if target_attr is not None:
                code = ""
                if takeoff_branch_map:
                    code = equipment_for_takeoff_branch(takeoff_branch_map, suffix)
                else:
                    code = _normalize_code(equipment_code)
                if code:
                    target_attr.dxf.text = code
                    wrote = True
        if not takeoff_branch_map:
            for tag in ("EQUIPMENT_CODE", "EQU"):
                target_attr = attrs_by_tag.get(tag)
                if target_attr is not None:
                    target_attr.dxf.text = _normalize_code(equipment_code)
                    wrote = True
    return wrote
