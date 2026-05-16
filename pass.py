"""按图块类型串联定位逻辑，输出 equipmentCode。"""

from typing import Dict, List, Optional, cast

from app.fid.utils.check_device import check_which_device

from . import common
from .match_id_short_family import (
    match_id_short_family_equipment_code,
    uses_id_short_uni_segment_rule,
)
from .match_new_inter import match_new_inter_equipment_code
from .match_takeoff import locator_keys_takeoff
from .match_vmb import locator_keys_vmb_slurry


def _locator_keys_for_block_type(block_type: str, attrs: Dict[str, str]) -> List[str]:
    if block_type == "TAKEOFF":
        return locator_keys_takeoff(attrs)
    if block_type in ("VMB_CHEMICAL", "VMB_GASNAME"):
        return locator_keys_vmb_slurry(attrs)
    if block_type == "NEW_INTER_":
        return []
    return []


def match_equipment_code(
    insert,
    by_uni_code: Dict[str, str],
    dxf_filename: Optional[str] = None,
    interfaces: Optional[List[dict]] = None,
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

    if uses_id_short_uni_segment_rule(block_type) and interfaces:
        hit = match_id_short_family_equipment_code(attrs, interfaces)
        if hit:
            return hit

    if block_type == "NEW_INTER_" and interfaces:
        hit = match_new_inter_equipment_code(attrs, interfaces)
        if hit:
            return hit

    keys = _locator_keys_for_block_type(block_type, attrs)
    hit = common.lookup_maps(keys, by_uni_code)
    if hit:
        return hit

    return common.match_equipment_code_legacy(attrs, by_uni_code)


def insert_matches_assigned_interface(insert, item: dict, dxf_filename: str) -> bool:
    """INSERT 是否与单条已派点接口一致（与 match_equipment_code 单条索引对齐）。"""
    if not common.interface_is_assigned(item):
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


def find_matched_assigned_interface(
    insert, interfaces: List[dict], dxf_filename: str
) -> Optional[dict]:
    """
    与本 INSERT 对应的入参接口行（Takeoff teeOffFlag/teeList 等按行策略依赖此项）。
    """
    for item in interfaces:
        if insert_matches_assigned_interface(insert, item, dxf_filename):
            return item

    attrs = common.insert_attrs_plain_upper(insert)
    if check_which_device(attrs, dxf_filename) != "TAKEOFF":
        return None
    ic = common.strip(attrs.get("INTERFACE_CODE"))
    if not ic:
        return None
    for item in interfaces:
        if not common.interface_is_assigned(item):
            continue
        if common.get_tee_off_flag(item) != 1:
            continue
        uc = common.strip(item.get("uniCode"))
        co = common.strip(item.get("code"))
        if ic == uc or ic == co:
            return item
    return None
