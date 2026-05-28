"""TakeOff：回填 EQUIPMENT_CODE（含 teeList 拼接）。"""

from typing import List

from . import common


def format_equipment_code_attr_text(matched_item: dict) -> str:
    """
    teeOffFlag==0：主档 equipmentCode；
    teeOffFlag==1：teeList 每项 lastSegment:equipmentCode，多项用 ';' 连接。
    """
    flag = common.get_tee_off_flag(matched_item)
    ec = str(matched_item.get("equipmentCode") or "").strip()
    tee_list = matched_item.get("teeList") or matched_item.get("tee_list") or []
    if flag != 1:
        return ec
    parts: List[str] = []
    for tee in tee_list:
        if not isinstance(tee, dict):
            continue
        uc = str(tee.get("uniCode") or tee.get("uni_code") or "").strip()
        teq = str(tee.get("equipmentCode") or tee.get("equipment_code") or "").strip()
        if not uc or not teq:
            continue
        segs = [s.strip() for s in uc.split(";") if str(s).strip()]
        last = segs[-1] if segs else ""
        if last:
            parts.append(f"{last}:{teq}")
    return ";".join(parts) if parts else ec


def write_takeoff_equipment_code(attrs_by_tag: dict, matched_item: dict) -> bool:
    eq_text = format_equipment_code_attr_text(matched_item)
    if not eq_text:
        return False
    target = attrs_by_tag.get("EQUIPMENT_CODE")
    if target is None:
        return False
    target.dxf.text = eq_text
    return True
