"""
SLD DXF 解析：仅依赖 ezdxf，与 app.fid 无耦合。

性能：先 INSERT + 图层过滤 + 读 ATTRIB，确认存在 ID_EquSubShort 属性（值可为空）后再算 bbox；
      bbox 默认 fast=True（大图纸更快）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import ezdxf
from ezdxf import bbox

from app.sld.constants import DEFAULT_BBOX_FAST
from app.sld.models import SldDevice

_SUB_DEVICE_TAGS = (
    "ID_EQUSUBSHORT",
    "ID_EQU_SUB_SHORT",
    "ID_EQUSUB_SHORT",
    "ID_EQU_SUBSHORT",
)


def _norm_tag(tag: Any) -> str:
    return str(tag).strip().upper()


def _norm_text(text: Any) -> str:
    if text is None:
        return ""
    return str(text).strip()


def _strip_leading_caret(s: str) -> str:
    s = s.strip()
    if s.startswith("^"):
        return s[1:].strip()
    return s


def _get_attr_if_present(attrs: Dict[str, str], *candidates: str) -> Optional[str]:
    """按候选 tag 顺序返回首个已存在属性的文本（允许为空字符串）。"""
    for k in candidates:
        if k in attrs:
            return attrs[k]
    return None


def _center_z_from_bbox(bb: Any, fallback: float) -> float:
    if bb is None:
        return float(fallback)
    try:
        return float((bb.extmin.z + bb.extmax.z) / 2)
    except Exception:
        return float(fallback)


def _compute_center(
    entity: Any,
    doc: Any,
    bbox_fast: bool,
) -> tuple[float, float, float]:
    ins = entity.dxf.insert
    try:
        bb = bbox.extents([entity], fast=bbox_fast)
        if bb is not None:
            cx = (bb.extmin.x + bb.extmax.x) / 2
            cy = (bb.extmin.y + bb.extmax.y) / 2
            cz = _center_z_from_bbox(bb, ins.z)
            return float(cx), float(cy), float(cz)
    except Exception:
        pass
    return float(ins.x), float(ins.y), float(ins.z)


def parse_sld_dxf(
    dxf_path: str | Path,
    target_layers: Optional[Sequence[str]] = None,
    *,
    bbox_fast: bool = DEFAULT_BBOX_FAST,
) -> List[SldDevice]:
    path = Path(dxf_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    tl_set: Optional[set[str]] = None
    if target_layers is not None:
        tl_set = {str(x).strip() for x in target_layers if str(x).strip()}

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    rows: List[SldDevice] = []

    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue

        layer = str(entity.dxf.layer)
        if tl_set is not None and layer not in tl_set:
            continue

        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            continue

        attrs: Dict[str, str] = {}
        raw_tags: List[str] = []
        for attr in entity.attribs:
            if not (hasattr(attr, "dxf") and hasattr(attr.dxf, "tag")):
                continue
            tag = _norm_tag(attr.dxf.tag)
            raw_tags.append(tag)
            attrs[tag] = _norm_text(getattr(attr.dxf, "text", None))

        sub_short = _get_attr_if_present(attrs, *_SUB_DEVICE_TAGS)
        if sub_short is None:
            continue
        id_equ = attrs.get("ID_EQU", "")

        cx, cy, cz = _compute_center(entity, doc, bbox_fast)

        tool_id = _strip_leading_caret(attrs["TOOL_ID"]) if attrs.get("TOOL_ID") else None

        rows.append(
            SldDevice(
                tool_id=tool_id,
                id_equ=id_equ or None,
                id_equ_sub_short=sub_short or None,
                owner=(attrs.get("OWNER", "") or attrs.get("EQU.GROUP", "")) or None,
                vendor=attrs.get("VENDOR", "") or None,
                model=attrs.get("MODEL", "") or None,
                bay_location=attrs.get("BAY_LOCATION", "") or None,
                records=attrs.get("RECORDS", "") or None,
                block_name=block_name,
                layer=layer,
                angle=float(entity.dxf.rotation) if hasattr(entity.dxf, "rotation") else 0.0,
                true_color=int(entity.dxf.color) if hasattr(entity.dxf, "color") else 0,
                insert_point_x=round(float(entity.dxf.insert.x), 4),
                insert_point_y=round(float(entity.dxf.insert.y), 4),
                insert_point_z=round(float(entity.dxf.insert.z), 4),
                center_point_x=round(float(cx), 4),
                center_point_y=round(float(cy), 4),
                center_point_z=round(float(cz), 4),
                block_id=str(entity.dxf.handle),
                raw_attrib_tags=sorted(set(raw_tags)),
            )
        )

    return rows


def sld_filename_stem_ok(stem: str) -> bool:
    """{任意}^SLD^{任意}^{任意}"""
    return bool(re.match(r"^.+\^SLD\^.+\^.+$", stem))
