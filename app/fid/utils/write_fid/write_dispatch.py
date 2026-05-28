"""按图块类型分发写入 EQUIPMENT_CODE / EQU*。"""

from typing import Dict, List, Optional

from app.fid.utils.write_fid.match_id_short_family import uses_id_short_uni_segment_rule
from app.fid.utils.write_fid.write_id_short_family import write_id_short_family_equipment_code
from app.fid.utils.write_fid.write_new_inter import write_new_inter_equipment_code
from app.fid.utils.write_fid.write_takeoff import write_takeoff_equipment_code
from app.fid.utils.write_fid.write_vmb import write_vmb_slurry_equipment_code


def dispatch_write_equipment_by_block_type(
    *,
    equipment_code: str,
    interface_code: str,
    id_code: str,
    block_type: str,
    attrs_plain: dict,
    attrs_by_tag: dict,
    matched_item: Optional[dict],
    is_takeoff_block: bool,
    takeoff_branch_map: Optional[Dict[str, str]] = None,
    matched_items: Optional[List[dict]] = None,
) -> bool:
    """
    根据图块类型写入属性；无 equipment_code 且非 takeoff tee-only 时由调用方跳过。
    返回是否至少写入一处属性。
    """
    if is_takeoff_block:
        if matched_item is not None:
            return write_takeoff_equipment_code(attrs_by_tag, matched_item)
        if equipment_code:
            target = attrs_by_tag.get("EQUIPMENT_CODE")
            if target is not None:
                target.dxf.text = equipment_code
                return True
        return False

    if block_type in ("VMB_CHEMICAL", "VMB_GASNAME"):
        return write_vmb_slurry_equipment_code(
            attrs_plain,
            attrs_by_tag,
            equipment_code,
            interface_code,
            id_code,
            takeoff_branch_map=takeoff_branch_map,
            matched_item=matched_item,
            matched_items=matched_items,
        )

    if uses_id_short_uni_segment_rule(block_type):
        return write_id_short_family_equipment_code(
            attrs_by_tag,
            equipment_code,
            matched_item=matched_item,
            matched_items=matched_items,
        )

    return write_new_inter_equipment_code(attrs_by_tag, equipment_code)
