"""FID 回填共用工具：属性读取、索引构建、通用查找。"""

from typing import Dict, List, Tuple


def strip(value) -> str:
    return str(value or "").strip()


def insert_attrs_plain_upper(insert) -> Dict[str, str]:
    """INSERT 块属性 tag(大写) -> text"""
    return {
        str(getattr(attrib.dxf, "tag", "") or "").upper(): strip(getattr(attrib.dxf, "text", ""))
        for attrib in getattr(insert, "attribs", [])
    }


def id_dot_entries(attrs: Dict[str, str]) -> List[Tuple[str, str]]:
    """收集 ID.x 端口属性（如 ID.1、ID.A），按 tag 排序。"""
    out: List[Tuple[str, str]] = []
    for tag in sorted(attrs.keys()):
        if not tag.startswith("ID.") or tag == "ID":
            continue
        if len(tag) < 4:
            continue
        val = attrs[tag].strip()
        if val:
            out.append((tag, val))
    return out


def dedupe_keys(keys: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for k in keys:
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def lookup_maps(keys: List[str], by_uni_code: Dict[str, str]) -> str:
    for k in keys:
        if k in by_uni_code:
            return by_uni_code[k]
    return ""


def match_equipment_code_legacy(attrs: Dict[str, str], by_uni_code: Dict[str, str]) -> str:
    """历史兜底：INTERFACE_CODE / ID 直接对齐 uniCode。"""
    interface_code = strip(attrs.get("INTERFACE_CODE"))
    if interface_code and interface_code in by_uni_code:
        return by_uni_code[interface_code]

    id_code = strip(attrs.get("ID"))
    if id_code and id_code in by_uni_code:
        return by_uni_code[id_code]

    return ""


def interface_is_assigned(item: dict) -> bool:
    """已派点：isAssigned 不为 3（仅 3 视为未派点）；缺省/非数字按已派点处理。"""
    v = item.get("isAssigned")
    if v is None:
        return True
    try:
        return int(v) != 3
    except (TypeError, ValueError):
        return True


def get_tee_off_flag(item: dict) -> int:
    v = item.get("teeOffFlag")
    if v is None:
        v = item.get("tee_off_flag")
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def parent_line_effective_assigned(item: dict) -> bool:
    """
    FID 回填用：字面已派(isAssigned≠3)时算已派点；
    若父行为未派点(isAssigned==3)但判定为「开 tee」(teeOffFlag==1)，则父行等同已派点参与索引与匹配。
    """
    if interface_is_assigned(item):
        return True
    return get_tee_off_flag(item) == 1


def build_assigned_indices(interfaces: List[dict]) -> Dict[str, str]:
    """提取已派点接口（含开 tee 的未字面派点父行），构建 uniCode -> equipmentCode 索引。"""
    by_uni_code: Dict[str, str] = {}

    for item in interfaces:
        if not parent_line_effective_assigned(item):
            continue
        equipment_code = str(item.get("equipmentCode") or "").strip()
        if not equipment_code:
            continue

        uni_code = str(item.get("uniCode") or "").strip()
        if uni_code:
            by_uni_code[uni_code] = equipment_code

    return by_uni_code

