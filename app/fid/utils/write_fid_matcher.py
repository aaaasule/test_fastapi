"""向后兼容：FID 定位匹配从 ``write_fid`` 子包重新导出。"""

from app.fid.utils.write_fid import (
    build_assigned_indices,
    find_matched_assigned_interface,
    get_tee_off_flag,
    id_dot_entries,
    id_short_family_equ_suffix_from_item,
    insert_attrs_plain_upper,
    insert_matches_assigned_interface,
    locator_keys_id_short_family,
    locator_keys_takeoff,
    locator_keys_vmb_slurry,
    match_equipment_code,
    match_id_short_family_equipment_code,
    match_new_inter_equipment_code,
    parent_line_effective_assigned,
    uses_id_short_uni_segment_rule,
)

__all__ = [
    "build_assigned_indices",
    "find_matched_assigned_interface",
    "get_tee_off_flag",
    "id_dot_entries",
    "id_short_family_equ_suffix_from_item",
    "insert_attrs_plain_upper",
    "insert_matches_assigned_interface",
    "locator_keys_id_short_family",
    "locator_keys_takeoff",
    "locator_keys_vmb_slurry",
    "match_equipment_code",
    "match_id_short_family_equipment_code",
    "match_new_inter_equipment_code",
    "parent_line_effective_assigned",
    "uses_id_short_uni_segment_rule",
]
