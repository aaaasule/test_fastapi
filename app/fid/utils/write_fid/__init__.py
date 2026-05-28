"""
FID DXF 回填：按图块类型拆分的定位与匹配子包。

对外稳定路径仍为：``app.fid.utils.write_fid_matcher``、``app.fid.utils.write_fid_writer``。
"""

from .common import (
    build_assigned_indices,
    dedupe_keys,
    get_tee_off_flag,
    id_dot_entries,
    insert_attrs_plain_upper,
    lookup_maps,
    match_equipment_code_legacy,
    parent_line_effective_assigned,
    strip,
)
from .match_id_short_family import (
    id_short_family_equ_suffix_from_item,
    locator_keys_id_short_family,
    match_id_short_family_equipment_code,
    uses_id_short_uni_segment_rule,
)
from .match_new_inter import match_new_inter_equipment_code
from .match_takeoff import locator_keys_takeoff
from .match_vmb import locator_keys_vmb_slurry
from .match_context import WriteFidMatchContext, build_write_fid_match_context
from .matching import (
    find_matched_assigned_interface,
    find_matched_assigned_interfaces,
    insert_matches_assigned_interface,
    match_equipment_code,
)

__all__ = [
    "build_assigned_indices",
    "dedupe_keys",
    "WriteFidMatchContext",
    "build_write_fid_match_context",
    "find_matched_assigned_interface",
    "find_matched_assigned_interfaces",
    "get_tee_off_flag",
    "id_dot_entries",
    "id_short_family_equ_suffix_from_item",
    "insert_attrs_plain_upper",
    "insert_matches_assigned_interface",
    "locator_keys_id_short_family",
    "locator_keys_takeoff",
    "locator_keys_vmb_slurry",
    "lookup_maps",
    "match_equipment_code",
    "match_equipment_code_legacy",
    "match_id_short_family_equipment_code",
    "parent_line_effective_assigned",
    "match_new_inter_equipment_code",
    "strip",
    "uses_id_short_uni_segment_rule",
]
