"""按图块类型串联定位逻辑，输出 equipmentCode。"""

from typing import Dict, List, Optional, cast

from app.fid.utils.check_device import check_which_device

from . import common
from .match_id_short_family import (
    find_id_short_matched_interfaces,
    id_short_item_matches_insert,
    match_id_short_family_equipment_code,
    uses_id_short_uni_segment_rule,
)
from .match_new_inter import match_new_inter_equipment_code
from .match_takeoff import locator_keys_takeoff
from .match_context import (
    WriteFidMatchContext,
    build_write_fid_match_context,
    collect_candidate_items_for_insert,
)
from .match_vmb import locator_keys_vmb_slurry, vmb_port_compounds_casefold


def _locator_keys_for_block_type(block_type: str, attrs: Dict[str, str]) -> List[str]:
    if block_type == "TAKEOFF":
        return locator_keys_takeoff(attrs)
    if block_type in ("VMB_CHEMICAL", "VMB_GASNAME"):
        return locator_keys_vmb_slurry(attrs)
    if block_type == "NEW_INTER_":
        return []
    return []


def _item_matches_insert_keys(
    attrs: Dict[str, str],
    block_type: str,
    item: dict,
    by_uni_code: Dict[str, str],
) -> bool:
    """用定位键交集 + equipmentCode 校验单条接口是否与图块一致。"""
    if not common.parent_line_effective_assigned(item):
        return False
    if block_type == "TAKEOFF" and common.get_tee_off_flag(item) == 1:
        ic = common.strip(attrs.get("INTERFACE_CODE"))
        uc = common.strip(item.get("uniCode"))
        co = common.strip(item.get("code"))
        return bool(ic and (ic == uc or ic == co))

    if uses_id_short_uni_segment_rule(block_type):
        return id_short_item_matches_insert(attrs, item)

    expected = common.strip(item.get("equipmentCode"))
    if not expected:
        return False

    keys = list(_locator_keys_for_block_type(block_type, attrs))
    ic = common.strip(attrs.get("INTERFACE_CODE"))
    if ic:
        keys.append(ic)
    id_code = common.strip(attrs.get("ID"))
    if id_code:
        keys.append(id_code)

    ec = common.lookup_maps(keys, by_uni_code)
    return bool(ec) and ec == expected


def match_equipment_code(
    insert,
    by_uni_code: Dict[str, str],
    dxf_filename: Optional[str] = None,
    interfaces: Optional[List[dict]] = None,
    match_ctx: Optional[WriteFidMatchContext] = None,
) -> str:
    """
    按图块类型做「定位属性」匹配，再查 uniCode -> equipmentCode。
    1) I_LINE/GPB 等：uniCode 第 3 段与图块 ID_SHORT 对齐
    2) NEW_INTER_：uniCode 第 3 段与 ID_SHORT 对齐
    3) VMB/Slurry：定位键「ID-ID.x 值」
    4) TakeOff：INTERFACE_CODE 等
    5) 最后 INTERFACE_CODE / ID 旧逻辑兜底

    兼容旧调用：match_equipment_code(insert, by_uni_code, interfaces)，第三参为 list 时视为 interfaces，
    dxf_filename 按空字符串处理（依赖属性兜底分支识别块类型）。
    """
    if isinstance(dxf_filename, list):
        interfaces = cast(List[dict], dxf_filename)
        dxf_filename = ""
    if dxf_filename is None:
        dxf_filename = ""
    if interfaces is None:
        interfaces = []

    attrs = common.insert_attrs_plain_upper(insert)
    block_type = check_which_device(attrs, dxf_filename)
    lookup = match_ctx.by_uni_code if match_ctx is not None else by_uni_code

    if uses_id_short_uni_segment_rule(block_type):
        hit = match_id_short_family_equipment_code(
            attrs, interfaces=interfaces, match_ctx=match_ctx
        )
        if hit:
            return hit

    if block_type == "NEW_INTER_":
        hit = match_new_inter_equipment_code(
            attrs, interfaces=interfaces, match_ctx=match_ctx
        )
        if hit:
            return hit

    keys = _locator_keys_for_block_type(block_type, attrs)
    hit = common.lookup_maps(keys, lookup)
    if hit:
        return hit

    return common.match_equipment_code_legacy(attrs, lookup)


def insert_matches_assigned_interface(insert, item: dict, dxf_filename: str) -> bool:
    """INSERT 是否与单条已派点接口一致（与 match_equipment_code 单条索引对齐）。"""
    if not common.parent_line_effective_assigned(item):
        return False

    attrs = common.insert_attrs_plain_upper(insert)
    if check_which_device(attrs, dxf_filename) == "TAKEOFF" and common.get_tee_off_flag(item) == 1:
        ic = common.strip(attrs.get("INTERFACE_CODE"))
        uc = common.strip(item.get("uniCode"))
        co = common.strip(item.get("code"))
        if ic and (ic == uc or ic == co):
            return True

    if not common.strip(item.get("equipmentCode")):
        return False
    by_u = common.build_assigned_indices([item])
    ec = match_equipment_code(insert, by_u, dxf_filename, [item])
    expected = common.strip(item.get("equipmentCode"))
    return bool(ec) and ec == expected


def _find_vmb_matched_interfaces(
    insert_attrs: Dict[str, str],
    interfaces: Optional[List[dict]] = None,
    match_ctx: Optional[WriteFidMatchContext] = None,
) -> List[dict]:
    """
    VMB/Slurry：按图块各端口定位键（ID-ID.x）直接关联入参 uniCode/code。
    提供 match_ctx 时按索引 O(端口数) 查找。
    """
    port_cf = vmb_port_compounds_casefold(insert_attrs)
    if not port_cf:
        return []

    if match_ctx is not None:
        matched: List[dict] = []
        seen_ids: set = set()
        for key in port_cf:
            for item in match_ctx.items_by_locator_cf.get(key, []):
                if not common.strip(item.get("equipmentCode")):
                    continue
                item_id = item.get("id")
                dedupe_key = item_id if item_id is not None else id(item)
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)
                matched.append(item)
        return matched

    if not interfaces:
        return []
    matched = []
    seen_ids: set = set()
    for item in interfaces:
        if not common.parent_line_effective_assigned(item):
            continue
        if not common.strip(item.get("equipmentCode")):
            continue
        hit = False
        for field in ("uniCode", "code"):
            v = common.strip(item.get(field))
            if v and v.casefold() in port_cf:
                hit = True
                break
        if not hit:
            continue
        item_id = item.get("id")
        dedupe_key = item_id if item_id is not None else id(item)
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        matched.append(item)
    return matched


def find_matched_assigned_interfaces(
    insert,
    interfaces: List[dict],
    dxf_filename: str,
    match_ctx: Optional[WriteFidMatchContext] = None,
) -> List[dict]:
    """
    与本 INSERT 对应的所有入参接口行（同一图块多端口/多分支时可能多条）。
    提供 match_ctx 时仅校验少量候选行，避免遍历全量 interfaces。
    """
    attrs = common.insert_attrs_plain_upper(insert)
    block_type = check_which_device(attrs, dxf_filename)

    if block_type in ("VMB_CHEMICAL", "VMB_GASNAME"):
        vmb_hits = _find_vmb_matched_interfaces(
            attrs, interfaces=interfaces, match_ctx=match_ctx
        )
        if vmb_hits:
            return vmb_hits

    if uses_id_short_uni_segment_rule(block_type):
        id_short_hits = find_id_short_matched_interfaces(
            attrs, interfaces=interfaces, match_ctx=match_ctx
        )
        if id_short_hits:
            return id_short_hits

    lookup = match_ctx.by_uni_code if match_ctx is not None else common.build_assigned_indices(
        interfaces
    )

    if match_ctx is not None:
        candidates = collect_candidate_items_for_insert(attrs, block_type, match_ctx)
        matched = [
            item
            for item in candidates
            if _item_matches_insert_keys(attrs, block_type, item, lookup)
        ]
        if matched:
            return matched
    else:
        matched = []
        seen_ids: set = set()
        for item in interfaces:
            if not insert_matches_assigned_interface(insert, item, dxf_filename):
                continue
            item_id = item.get("id")
            dedupe_key = item_id if item_id is not None else id(item)
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            matched.append(item)
        if matched:
            return matched

    if block_type != "TAKEOFF":
        return []
    ic = common.strip(attrs.get("INTERFACE_CODE"))
    if not ic:
        return []
    if match_ctx is not None:
        for item in match_ctx.items_by_locator_cf.get(ic.casefold(), []):
            if not common.parent_line_effective_assigned(item):
                continue
            if common.get_tee_off_flag(item) != 1:
                continue
            uc = common.strip(item.get("uniCode"))
            co = common.strip(item.get("code"))
            if ic == uc or ic == co:
                return [item]
    for item in interfaces:
        if not common.parent_line_effective_assigned(item):
            continue
        if common.get_tee_off_flag(item) != 1:
            continue
        uc = common.strip(item.get("uniCode"))
        co = common.strip(item.get("code"))
        if ic == uc or ic == co:
            return [item]
    return []


def find_matched_assigned_interface(
    insert, interfaces: List[dict], dxf_filename: str
) -> Optional[dict]:
    """
    与本 INSERT 对应的首条入参接口行（Takeoff teeOffFlag/teeList 等仍用单条策略）。
    """
    items = find_matched_assigned_interfaces(
        insert, interfaces, dxf_filename, match_ctx=None
    )
    return items[0] if items else None
