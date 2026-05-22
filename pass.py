"""规范性校验公共工具：业务键 + 详情模板 + 关键属性配置。"""
from __future__ import annotations

from typing import Dict, Tuple

from app.sld.models import SldDevice

# 关键业务属性（用于必填/缺失校验）
ERROR_KEY_ATTRS: Tuple[str, ...] = ("ID_EQU", "ID_EquSubShort")
WARNING_KEY_ATTRS: Tuple[str, ...] = ("OWNER", "VENDOR", "MODEL")
KEY_ATTRS: Tuple[str, ...] = ERROR_KEY_ATTRS + WARNING_KEY_ATTRS
KEY_ATTR_KEYS: Dict[str, str] = {
    "ID_EQU": "id_equ",
    "ID_EquSubShort": "id_equ_sub_short",
    "OWNER": "owner",
    "VENDOR": "vendor",
    "MODEL": "model",
}

# 与 parser 中 ATTRIB tag 一致（大写），用于区分「无 tag」与「有 tag 但值为空」
KEY_ATTR_DXF_TAGS: Dict[str, Tuple[str, ...]] = {
    "ID_EQU": ("ID_EQU",),
    "ID_EquSubShort": (
        "ID_EQUSUBSHORT",
        "ID_EQU_SUB_SHORT",
        "ID_EQUSUB_SHORT",
        "ID_EQU_SUBSHORT",
    ),
    "OWNER": ("OWNER", "EQU.GROUP"),
    "VENDOR": ("VENDOR",),
    "MODEL": ("MODEL",),
}


def business_key(d: SldDevice) -> str:
    """业务键：``"<id_equ>+<id_equ_sub_short>"``，未填字段保留为空。"""
    ie = (d.id_equ or "").strip()
    sub = (d.id_equ_sub_short or "").strip()
    return f"{ie}+{sub}"


def base_detail(d: SldDevice) -> dict:
    """各 spec issue.detail 的公共字段。"""
    return {
        "ID_EQU+ID_EquSubShort": business_key(d),
        "坐标X": d.center_point_x,
        "坐标Y": d.center_point_y,
        "TOOL_ID": d.tool_id,
        "block_id": d.block_id,
    }


def attr_on_device(d: SldDevice, logical: str) -> str | None:
    """根据逻辑字段名（KEY_ATTRS 之一）取设备上的实际属性值。"""
    key = KEY_ATTR_KEYS[logical]
    return getattr(d, key, None)


def _raw_tag_set(d: SldDevice) -> set[str]:
    return {str(t).strip().upper() for t in (d.raw_attrib_tags or [])}


def attrib_tag_present(d: SldDevice, logical: str) -> bool:
    """图块 ATTRIB 中是否包含该逻辑字段对应的任一 DXF tag。"""
    tags = _raw_tag_set(d)
    for candidate in KEY_ATTR_DXF_TAGS.get(logical, ()):
        if candidate.upper() in tags:
            return True
    return False


def attr_value_empty(val: str | None) -> bool:
    """属性值视为未填写：None 或空白字符串。"""
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() == ""
    return False
