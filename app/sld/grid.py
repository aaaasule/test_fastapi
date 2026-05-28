"""
SLD 柱网匹配：自包含实现（不引用 app.fid）。

根据柱网定义行（field / axis / valueFrom / valueTo）生成柱心网格，
对设备 center_point 做 KD 树批量最近邻查询。
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
from scipy.spatial import cKDTree

from app.sld.models import SldDevice


class SldGridMatcher:
    def __init__(
        self,
        grid_rows: Sequence[dict],
    ):
        """
        grid_rows: 每项含 field, axis(X|Y), valueFrom, valueTo（与前端 gridList 对齐）
        """
        fields: List[str] = []
        axes: List[str] = []
        v_from: List[float] = []
        v_to: List[float] = []
        for row in grid_rows:
            fields.append(str(row.get("field", "")).strip())
            axes.append(str(row.get("axis", row.get("XY", ""))).strip().upper())
            v_from.append(float(row.get("valueFrom", row.get("value_from", 0))))
            v_to.append(float(row.get("valueTo", row.get("value_to", 0))))

        if not (len(fields) == len(axes) == len(v_from) == len(v_to)):
            raise ValueError("柱网定义行字段长度不一致")

        x_fields, x_coords, y_fields, y_coords = [], [], [], []
        for f, axis, v0, _v1 in zip(fields, axes, v_from, v_to):
            if axis == "X":
                x_fields.append(f)
                x_coords.append(v0)
            elif axis == "Y":
                y_fields.append(f)
                y_coords.append(v0)
            else:
                raise ValueError(f"柱网 axis 仅支持 X/Y，当前: {axis}")

        if not x_fields or not y_fields:
            raise ValueError("柱网定义须同时包含 X 与 Y 方向")

        self._pillars: List[Tuple[str, str, float, float]] = [
            (xf, yf, x, y)
            for xf, x in zip(x_fields, x_coords)
            for yf, y in zip(y_fields, y_coords)
        ]
        coords_array = np.array([(x, y) for xf, yf, x, y in self._pillars], dtype=np.float64)
        self._tree = cKDTree(coords_array)
        self._pillar_names: List[Tuple[str, str]] = [
            (name_x, name_y) for name_x, name_y, _x, _y in self._pillars
        ]

    def apply_to_devices(self, devices: List[SldDevice]) -> None:
        """就地写入 grid_x / grid_y。"""
        if not devices:
            return
        coords = np.array([(d.center_point_x, d.center_point_y) for d in devices], dtype=np.float64)
        _, indices = self._tree.query(coords)
        for d, idx in zip(devices, indices):
            gx, gy = self._pillar_names[int(idx)]
            d.grid_x = gx
            d.grid_y = gy
