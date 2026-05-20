"""设备删除校验：历史业务键 - 当前业务键。

除产出 warning 外，对外暴露 ``build_deleted_devices`` —— 把"已删除"
的历史项构造成 ``operation="delete"`` 的 SldDevice 幽灵对象，便于
checker 追加到 eqpData 输出，让前端可以拿到完整的增/删/改集合。
"""
from __future__ import annotations

from typing import List, Set

from app.sld.models import SldDevice, SldIssue
from app.sld.validators.changes.base import BaseChangeRule
from app.sld.validators.changes.common import (
    HistoryIndex,
    build_history_index,
    hist_float,
    hist_id_equ,
    hist_id_equ_sub_short,
    hist_str,
)
from app.sld.validators.specs.common import business_key


def _curr_biz_keys(current: List[SldDevice]) -> Set[str]:
    out: Set[str] = set()
    for d in current:
        k = business_key(d)
        if k.strip("+") and k != "+":
            out.add(k)
    return out


class DeletedRule(BaseChangeRule):
    name = "设备删除"
    type = "warning"
    order = 120

    def check(
        self,
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        issues: List[SldIssue] = []
        curr_keys = _curr_biz_keys(current)
        for k in history.by_biz.keys() - curr_keys:
            issues.append(
                SldIssue(
                    type="warning",
                    name="设备删除",
                    description="和上一版数据相比设备删除",
                    detail={"ID_EQU+ID_EquSubShort": k},
                )
            )
        return issues


def _device_from_history(item: dict) -> SldDevice:
    """把历史项映射成最小可用的 SldDevice（仅填能拿到的字段）。"""
    id_equ = hist_id_equ(item) or None
    sub = hist_id_equ_sub_short(item) or None
    tool_id = hist_str(item, "toolId", "tool_id") or None
    return SldDevice(
        id_equ=id_equ,
        id_equ_sub_short=sub,
        tool_id=tool_id,
        owner=hist_str(item, "owner") or None,
        vendor=hist_str(item, "vendor") or None,
        model=hist_str(item, "model") or None,
        bay_location=hist_str(item, "bayLocation", "bay_location") or None,
        records=hist_str(item, "records") or None,
        grid_x=hist_str(item, "gridX", "grid_x") or None,
        grid_y=hist_str(item, "gridY", "grid_y") or None,
        block_name=hist_str(item, "blockName", "block_name"),
        layer=hist_str(item, "layer"),
        angle=hist_float(item, "angle"),
        true_color=int(hist_float(item, "trueColor", "true_color")),
        insert_point_x=hist_float(item, "insertPointX", "insert_point_x"),
        insert_point_y=hist_float(item, "insertPointY", "insert_point_y"),
        insert_point_z=hist_float(item, "insertPointZ", "insert_point_z"),
        center_point_x=hist_float(item, "centerPointX", "center_point_x"),
        center_point_y=hist_float(item, "centerPointY", "center_point_y"),
        center_point_z=hist_float(item, "centerPointZ", "center_point_z"),
        block_id=hist_str(item, "blockId", "block_id"),
        operation="delete",
        eld_source_row=item,
    )


def build_deleted_devices(
    current: List[SldDevice],
    eld_sub_equipment_list: List[dict],
) -> List[SldDevice]:
    """构造 ``operation="delete"`` 的幽灵设备列表。

    与 ``DeletedRule`` 复用同一份历史索引语义：上一版（``eldSubEquipmentList``）业务键存在但
    当前 DXF 解析结果中缺失的，即为已删除。
    """
    history = build_history_index(eld_sub_equipment_list)
    curr_keys = _curr_biz_keys(current)
    out: List[SldDevice] = []
    for k in history.by_biz.keys() - curr_keys:
        out.append(_device_from_history(history.by_biz[k]))
    return out
