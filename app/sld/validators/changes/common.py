"""变更校验公共工具：历史索引构建 + 字段抽取。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


def hist_id_equ(item: Dict[str, Any]) -> str:
    """历史项 ID_EQU（兼容 EFMS ``equipmentCode`` / 编组 ``code``）。"""
    return hist_str(item, "idEqu", "id_equ", "equipmentCode", "code")


def hist_id_equ_sub_short(item: Dict[str, Any]) -> str:
    """历史项 ID_EquSubShort（兼容 EFMS ``equSubShort``）。"""
    return hist_str(item, "idEquSubShort", "id_equ_sub_short", "equSubShort")


def hist_key(item: Dict[str, Any]) -> str:
    """历史项的业务键（与 spec.business_key 同口径）。

    若仅有 ``code`` / ``equipmentCode``（常见于 ELD 子设备列表），则退化为 ``"{code}+"``，
    与图面仅 ID_EQU、无子短码时的 ``business_key`` 对齐。
    """
    ie = hist_id_equ(item)
    sub = hist_id_equ_sub_short(item)
    if ie or sub:
        return f"{ie}+{sub}"
    return "+"


def hist_tool_id(item: Dict[str, Any]) -> str:
    return str(item.get("toolId") or item.get("tool_id") or "").strip()


def hist_float(item: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
    """按候选键依次取浮点值，失败则返回默认值。"""
    for k in keys:
        if k in item and item[k] is not None:
            try:
                return float(item[k])
            except (TypeError, ValueError):
                pass
    return default


def hist_str(item: Dict[str, Any], *keys: str) -> str:
    for k in keys:
        if k in item and item[k] is not None:
            return str(item[k]).strip()
    return ""


def hist_device_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    """历史项中参与变更比对的子集（snake_case）。"""
    return {
        "group_code": hist_str(item, "groupCode", "group_code", "owner"),
        "vendor": hist_str(item, "vendor"),
        "model": hist_str(item, "model"),
        "bay_location": hist_str(item, "bayLocation", "bay_location"),
        "center_x": hist_float(item, "centerPointX", "center_point_x"),
        "center_y": hist_float(item, "centerPointY", "center_point_y"),
    }


@dataclass
class HistoryIndex:
    """上一版 ``eldSubEquipmentList``（子设备/ELD 行）的索引视图。

    - by_biz: 业务键(ID_EQU+ID_EquSubShort 或 code+) → 历史项
    - by_tool: TOOL_ID → 历史项
    - raw: 已过滤 status 后的原始历史项序列
    """

    by_biz: Dict[str, Dict[str, Any]]
    by_tool: Dict[str, Dict[str, Any]]
    raw: List[Dict[str, Any]]


def build_history_index(eld_sub_equipment_list: List[Dict[str, Any]]) -> HistoryIndex:
    """根据上一版 ``eldSubEquipmentList`` 构造索引；status 以 ``not`` 开头视为已废弃。"""
    by_biz: Dict[str, Dict[str, Any]] = {}
    by_tool: Dict[str, Dict[str, Any]] = {}
    raw: List[Dict[str, Any]] = []
    for item in eld_sub_equipment_list or []:
        status = str(item.get("status", "")).lower()
        if status.startswith("not"):
            continue
        raw.append(item)
        hk = hist_key(item)
        if hk and hk != "+":
            by_biz[hk] = item
        tid = hist_tool_id(item)
        if tid:
            by_tool[tid] = item
    return HistoryIndex(by_biz=by_biz, by_tool=by_tool, raw=raw)
