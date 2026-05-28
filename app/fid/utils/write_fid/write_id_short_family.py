"""I_LINE、GPB、母线插板槽：按匹配行末段写入 EQU.{末段}。"""

from typing import List, Optional

from . import common
from .match_id_short_family import id_short_family_equ_suffix_from_item


def write_id_short_family_equipment_code(
    attrs_by_tag: dict,
    equipment_code: str,
    matched_item: Optional[dict] = None,
    matched_items: Optional[List[dict]] = None,
) -> bool:
    items = matched_items or ([matched_item] if matched_item is not None else [])
    if not items:
        return False

    wrote = False
    for item in items:
        last_seg = id_short_family_equ_suffix_from_item(item)
        if not last_seg:
            continue
        equ_dot_tag = f"EQU.{last_seg.upper()}"
        target_attr = attrs_by_tag.get(equ_dot_tag)
        if target_attr is None:
            continue
        ec = common.strip(item.get("equipmentCode")) or equipment_code
        if not ec:
            continue
        target_attr.dxf.text = ec
        wrote = True
    return wrote
