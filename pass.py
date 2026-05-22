import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ezdxf

from app.fid.utils.check_device import check_which_device
from app.fid.utils.write_fid.common import (
    build_assigned_indices,
    get_tee_off_flag,
    insert_attrs_plain_upper,
    parent_line_effective_assigned,
)
from app.fid.utils.write_fid.matching import (
    find_matched_assigned_interface,
    match_equipment_code,
)
from app.fid.utils.write_fid.write_dispatch import dispatch_write_equipment_by_block_type

WRITE_FID_OUTPUT_REL_DIR = "fid_with_assignment"
WRITE_FID_OUTPUT_ABS_DIR = Path("/EFMS") / WRITE_FID_OUTPUT_REL_DIR
# FTP 上传远端路径前缀（与服务器目录 /EFMS/fid_with_assignment 对应）
WRITE_FID_FTP_REMOTE_PREFIX = "EFMS/fid_with_assignment"
TAKEOFF_DEFAULT_COLOR = 8
TAKEOFF_ASSIGNED_COLOR = 1
TAKEOFF_SYSTEM_CODES = {"PA", "PD", "PE", "PV", "PP", "PW"}
MIXED_TAKEOFF_SYSTEM_CODES = {"PB"}


def _normalize_code(value: str) -> str:
    return str(value or "").strip()


def _get_last_segment(value: str) -> str:
    code = _normalize_code(value)
    if not code:
        return ""
    return code.split(";")[-1].strip()


def _build_takeoff_base_key(value: str) -> str:
    """
    将 tee 分支编码转为主接口编码：
    例如 PCWS;FAB2F1;2aWS04;02-A -> PCWS;FAB2F1;2aWS04;02
    """
    code = _normalize_code(value)
    if not code:
        return ""
    parts = code.split(";")
    if not parts:
        return ""
    tail = parts[-1].strip()
    if "-" not in tail:
        return ""
    base_tail = tail.rsplit("-", 1)[0].strip()
    if not base_tail:
        return ""
    return ";".join(parts[:-1] + [base_tail])


def _build_takeoff_group_map(interfaces: List[dict]) -> Dict[str, Dict[str, str]]:
    """
    将已派点 tee 分支聚合到主接口：
    base_code -> {branch_label: equipment_code}

    父行字面未派但 teeOffFlag==1 等同已派点时，仍按父行 uniCode 参与分支聚合。
    """
    grouped: Dict[str, Dict[str, str]] = {}
    for item in interfaces:
        if not parent_line_effective_assigned(item):
            continue
        equipment_code = _normalize_code(item.get("equipmentCode"))
        if not equipment_code:
            continue

        for key in (_normalize_code(item.get("uniCode")), _normalize_code(item.get("code"))):
            if not key:
                continue
            base_key = _build_takeoff_base_key(key)
            if not base_key:
                continue
            branch_label = _get_last_segment(key)
            if not branch_label:
                continue

            if base_key not in grouped:
                grouped[base_key] = {}
            grouped[base_key][branch_label] = equipment_code
    return grouped


def _filename_suggests_takeoff(dxf_filename: str) -> bool:
    """systemCode 为空时根据路径中的 FID.Px 判断是否 Takeoff 图。"""
    fn = _normalize_code(dxf_filename).upper().replace("^", ".")
    for tail in TAKEOFF_SYSTEM_CODES | MIXED_TAKEOFF_SYSTEM_CODES:
        if f"FID.{tail}" in fn:
            return True
    return False


def _is_takeoff_interface_by_system(item: dict) -> bool:
    """
    参考 check_device 规则，优先按 systemCode 判断是否属于 Takeoff。
    """
    system_code = _normalize_code(item.get("systemCode")).upper()
    if system_code in TAKEOFF_SYSTEM_CODES:
        return True
    if system_code in MIXED_TAKEOFF_SYSTEM_CODES:
        # PB 既可能是 takeoff 也可能是 vmb，接口编码存在时按 takeoff 处理
        return bool(_normalize_code(item.get("uniCode")) or _normalize_code(item.get("code")))
    return False


def _build_takeoff_targets(interfaces: List[dict], dxf_filename: str) -> Tuple[set, set]:
    """
    基于「有效已派」（含 teeOffFlag==1）+ takeoff(systemCode / FID 文件名) 构建着色命中目标：
    - takeoff_code_keys: 接口编码键（含 tee 主接口键）
    - takeoff_block_ids: 句柄键(cadBlockId)
    """
    takeoff_code_keys = set()
    takeoff_block_ids = set()

    for item in interfaces:
        if not parent_line_effective_assigned(item):
            continue
        if not _normalize_code(item.get("equipmentCode")):
            continue
        takeoff_subject = (
            _is_takeoff_interface_by_system(item)
            or _filename_suggests_takeoff(dxf_filename)
        )
        if not takeoff_subject:
            continue

        for key in (_normalize_code(item.get("uniCode")), _normalize_code(item.get("code"))):
            if not key:
                continue
            takeoff_code_keys.add(key)
            base_key = _build_takeoff_base_key(key)
            if base_key:
                takeoff_code_keys.add(base_key)

        cad_block_id = _normalize_code(item.get("cadBlockId"))
        if cad_block_id:
            takeoff_block_ids.add(cad_block_id)

    return takeoff_code_keys, takeoff_block_ids


def _is_takeoff_insert(
    insert,
    interface_code: str,
    id_code: str,
    takeoff_code_keys: set,
    takeoff_block_ids: set,
) -> bool:
    handle = _normalize_code(getattr(insert.dxf, "handle", ""))
    if handle and handle in takeoff_block_ids:
        return True

    for code in (interface_code, id_code):
        value = _normalize_code(code)
        if not value:
            continue
        if value in takeoff_code_keys:
            return True
        base_key = _build_takeoff_base_key(value)
        if base_key and base_key in takeoff_code_keys:
            return True
    return False


def _is_takeoff_like_code(interface_code: str) -> bool:
    code = _normalize_code(interface_code).upper()
    if not code:
        return False
    tail = _get_last_segment(code)
    if "-" in tail:
        return True
    return code.startswith("PCWS;")


def _format_takeoff_group_value(branch_map: Dict[str, str]) -> str:
    if not branch_map:
        return ""
    # 排序确保输出稳定，便于比对
    items = [f"{k}:{branch_map[k]}" for k in sorted(branch_map)]
    return ";".join(items)


def _safe_set_entity_color(entity, color_index: int) -> bool:
    """
    设置实体颜色（ACI 索引），返回是否成功设置。
    """
    try:
        _ = entity.dxf.color
        entity.dxf.color = color_index
        return True
    except Exception:
        return False


def _resolve_equipment_code_for_insert(
    insert,
    by_uni_code: Dict[str, str],
    takeoff_group_map: Dict[str, Dict[str, str]],
    dxf_filename: str,
    interfaces: List[dict],
):
    attrs_by_tag = {
        str(getattr(attrib.dxf, "tag", "") or "").upper(): attrib
        for attrib in getattr(insert, "attribs", [])
    }
    interface_code = _normalize_code(
        (attrs_by_tag.get("INTERFACE_CODE").dxf.text if attrs_by_tag.get("INTERFACE_CODE") else "")
    )
    id_code = _normalize_code((attrs_by_tag.get("ID").dxf.text if attrs_by_tag.get("ID") else ""))

    equipment_code = match_equipment_code(insert, by_uni_code, dxf_filename, interfaces)
    takeoff_branch_map: Optional[Dict[str, str]] = None
    if not equipment_code:
        takeoff_key = interface_code or id_code
        if takeoff_key and takeoff_key in takeoff_group_map:
            takeoff_branch_map = dict(takeoff_group_map[takeoff_key])
            equipment_code = _format_takeoff_group_value(takeoff_branch_map)

    return equipment_code, interface_code, id_code, attrs_by_tag, takeoff_branch_map


def _paint_insert_visual_bundle(insert, color_index: int) -> int:
    """Takeoff INSERT 本体 + 挂载 ATTRIB 统一着色（ACI）；返回实际改成功的实体个数。"""
    n = 0
    if _safe_set_entity_color(insert, color_index):
        n += 1
    for attrib in getattr(insert, "attribs", []):
        if _safe_set_entity_color(attrib, color_index):
            n += 1
    return n


def apply_takeoff_colors(
    doc: ezdxf.document.Drawing,
    interfaces: List[dict],
    dxf_filename: str,
    default_color: int = TAKEOFF_DEFAULT_COLOR,
    assigned_color: int = TAKEOFF_ASSIGNED_COLOR,
) -> Tuple[int, int]:
    """
    Takeoff 图块颜色策略（仅作用于块类型识别为 TAKEOFF 的 INSERT）：
    1）先将这些 INSERT（含其可见 ATTRIB）统一改为灰色（默认 ACI=8）
    2）再将命中「已派点」逻辑的 INSERT（含 ATTRIB）改为红色（默认 ACI=1）
    返回：(灰色涂刷涉及的实体计数[INSERT + 其 ATTRIB], 视为已派并标红的 INSERT 个数)
    """
    msp = doc.modelspace()

    takeoff_inserts_all: List = []
    for insert in msp.query("INSERT"):
        attrs_plain = insert_attrs_plain_upper(insert)
        if check_which_device(attrs_plain, dxf_filename) != "TAKEOFF":
            continue
        takeoff_inserts_all.append(insert)

    if not takeoff_inserts_all:
        return 0, 0

    by_uni_code = build_assigned_indices(interfaces)
    takeoff_group_map = _build_takeoff_group_map(interfaces)
    takeoff_code_keys, takeoff_block_ids = _build_takeoff_targets(interfaces, dxf_filename)

    assigned_inserts: List = []
    for insert in takeoff_inserts_all:
        equipment_code, interface_code, id_code, _, _ = _resolve_equipment_code_for_insert(
            insert,
            by_uni_code,
            takeoff_group_map,
            dxf_filename,
            interfaces,
        )
        if not equipment_code:
            continue
        if _is_takeoff_insert(insert, interface_code, id_code, takeoff_code_keys, takeoff_block_ids):
            assigned_inserts.append(insert)
            continue
        code_for_type = interface_code or id_code
        if _is_takeoff_like_code(code_for_type):
            assigned_inserts.append(insert)

    total_gray_entities = 0
    for insert in takeoff_inserts_all:
        total_gray_entities += _paint_insert_visual_bundle(insert, default_color)

    highlighted = 0
    for insert in assigned_inserts:
        _paint_insert_visual_bundle(insert, assigned_color)
        highlighted += 1

    return total_gray_entities, highlighted


def clear_equ_attributes(doc: ezdxf.document.Drawing) -> int:
    """清空图纸内 EQUIPMENT_CODE 及所有 EQU* 属性文本，仅保留属性结构。"""
    cleared = 0
    msp = doc.modelspace()
    for insert in msp.query("INSERT"):
        for attrib in getattr(insert, "attribs", []):
            tag = str(getattr(attrib.dxf, "tag", "") or "").upper()
            if tag == "EQUIPMENT_CODE" or tag.startswith("EQU"):
                if (attrib.dxf.text or "") != "":
                    attrib.dxf.text = ""
                    cleared += 1
    return cleared


def write_equipment_code(
    doc: ezdxf.document.Drawing, interfaces: List[dict], dxf_filename: str
) -> Tuple[int, int]:
    """
    在已清空 EQU* 后，按已派点数据回填 EQUIPMENT_CODE / EQU。
    返回：(已派点接口数量, 实际回填次数)
    """
    by_uni_code = build_assigned_indices(interfaces)
    takeoff_group_map = _build_takeoff_group_map(interfaces)
    assigned_count = sum(
        1
        for item in interfaces
        if parent_line_effective_assigned(item) and _normalize_code(item.get("equipmentCode"))
    )
    written = 0

    msp = doc.modelspace()
    for insert in msp.query("INSERT"):
        equipment_code, interface_code, id_code, attrs_by_tag, takeoff_branch_map = (
            _resolve_equipment_code_for_insert(
            insert,
            by_uni_code,
            takeoff_group_map,
            dxf_filename,
            interfaces,
        )
        )

        attrs_plain = insert_attrs_plain_upper(insert)
        block_type = check_which_device(attrs_plain, dxf_filename)
        matched_item = find_matched_assigned_interface(insert, interfaces, dxf_filename)

        is_takeoff_block = block_type == "TAKEOFF"
        can_takeoff_tee_only = (
            is_takeoff_block
            and matched_item is not None
            and get_tee_off_flag(matched_item) == 1
        )

        if not equipment_code and not can_takeoff_tee_only:
            continue

        wrote_for_insert = dispatch_write_equipment_by_block_type(
            block_type=block_type,
            attrs_plain=attrs_plain,
            attrs_by_tag=attrs_by_tag,
            equipment_code=equipment_code,
            interface_code=interface_code,
            id_code=id_code,
            matched_item=matched_item,
            is_takeoff_block=is_takeoff_block,
            takeoff_branch_map=takeoff_branch_map,
        )

        if wrote_for_insert:
            written += 1

    return assigned_count, written


def build_write_fid_output_path(file_path: str) -> Tuple[Path, str]:
    src_name = Path(file_path).name
    stem = Path(src_name).stem
    suffix = Path(src_name).suffix or ".dxf"
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    out_name = f"{stem}_{ts}{suffix}"
    out_file = WRITE_FID_OUTPUT_ABS_DIR / out_name
    rel_path = f"{WRITE_FID_OUTPUT_REL_DIR}/{out_name}"
    return out_file, rel_path


def build_write_fid_ftp_result_names(source_stem: str) -> Tuple[str, str, str]:
    """
    回填结果文件名、FTP 上传路径与 API 响应 data 路径。
    返回 (out_filename, ftp_remote_path, api_data_path)：
    - ftp_remote_path: EFMS/fid_with_assignment/{stem}_{时间戳}.dxf
    - api_data_path: fid_with_assignment/{stem}_{时间戳}.dxf
    """
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    out_name = f"{source_stem}_{ts}.dxf"
    ftp_remote_path = f"{WRITE_FID_FTP_REMOTE_PREFIX}/{out_name}"
    api_data_path = f"{WRITE_FID_OUTPUT_REL_DIR}/{out_name}"
    return out_name, ftp_remote_path, api_data_path
