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
    

    if is_takeoff_block:
        if matched_item is not None:
            return write_takeoff_equipment_code(attrs_by_tag, matched_item)
        if equipment_code:
            target = attrs_by_tag.get("EQUIPMENT_CODE")
            if target is not None:
                target.dxf.text = equipment_code
                return True
        return False



