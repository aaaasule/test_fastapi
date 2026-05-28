"""FID 回填：接口列表预索引，避免「每个 INSERT × 全量 interfaces」扫描。"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set

from . import common


@dataclass
class WriteFidMatchContext:
    """一次回填请求内复用的匹配索引。"""

    by_uni_code: Dict[str, str] = field(default_factory=dict)
    items_by_locator_cf: Dict[str, List[dict]] = field(default_factory=dict)
    items_by_id_short: Dict[str, List[dict]] = field(default_factory=dict)


def build_write_fid_match_context(interfaces: List[dict]) -> WriteFidMatchContext:
    """
    预构建 uniCode/code/定位键 -> equipmentCode 与接口行列表。
    复杂度 O(len(interfaces))，在遍历 INSERT 前只执行一次。
    """
    by_uni_code: Dict[str, str] = {}
    items_by_locator_cf: Dict[str, List[dict]] = defaultdict(list)
    items_by_id_short: Dict[str, List[dict]] = defaultdict(list)

    for item in interfaces:
        if not common.parent_line_effective_assigned(item):
            continue
        equipment_code = common.strip(item.get("equipmentCode"))
        tee_parent_no_equipment = (
            not equipment_code and common.get_tee_off_flag(item) == 1
        )
        if not equipment_code and not tee_parent_no_equipment:
            continue

        for field in ("uniCode", "code"):
            locator = common.strip(item.get(field))
            if not locator:
                continue
            if equipment_code:
                by_uni_code[locator] = equipment_code
            items_by_locator_cf[locator.casefold()].append(item)

            parts = [p.strip() for p in locator.split(";")]
            if len(parts) >= 3:
                id_short = parts[2]
                if id_short:
                    items_by_id_short[id_short].append(item)

    return WriteFidMatchContext(
        by_uni_code=by_uni_code,
        items_by_locator_cf=dict(items_by_locator_cf),
        items_by_id_short=dict(items_by_id_short),
    )


def _locator_keys_for_block_type(block_type: str, attrs: Dict[str, str]) -> List[str]:
    if block_type == "TAKEOFF":
        from .match_takeoff import locator_keys_takeoff

        return locator_keys_takeoff(attrs)
    if block_type in ("VMB_CHEMICAL", "VMB_GASNAME"):
        from .match_vmb import locator_keys_vmb_slurry

        return locator_keys_vmb_slurry(attrs)
    return []


def _dedupe_items(items: List[dict]) -> List[dict]:
    matched: List[dict] = []
    seen_ids: set = set()
    for item in items:
        item_id = item.get("id")
        dedupe_key = item_id if item_id is not None else id(item)
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        matched.append(item)
    return matched


def collect_candidate_items_for_insert(
    attrs: Dict[str, str],
    block_type: str,
    ctx: WriteFidMatchContext,
) -> List[dict]:
    """根据图块属性键从索引中取候选接口行（通常 0～几条）。"""
    cf_keys: Set[str] = set()

    interface_code = common.strip(attrs.get("INTERFACE_CODE"))
    if interface_code:
        cf_keys.add(interface_code.casefold())

    id_code = common.strip(attrs.get("ID"))
    if id_code:
        cf_keys.add(id_code.casefold())

    for key in _locator_keys_for_block_type(block_type, attrs):
        if key:
            cf_keys.add(key.casefold())

    if block_type not in ("TAKEOFF", "VMB_CHEMICAL", "VMB_GASNAME", "NEW_INTER_"):
        id_short = common.strip(attrs.get("ID_SHORT"))
        if id_short:
            return _dedupe_items(list(ctx.items_by_id_short.get(id_short, [])))

    candidates: List[dict] = []
    seen_ids: set = set()
    for cf in cf_keys:
        for item in ctx.items_by_locator_cf.get(cf, []):
            item_id = item.get("id")
            dedupe_key = item_id if item_id is not None else id(item)
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            candidates.append(item)
    return candidates
