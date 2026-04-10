# import numpy as np
# from scipy.spatial import cKDTree
# from typing import List, Tuple, Dict
#
# from ..base_rules import BaseRule, Equipment, CheckResult
#
#
# class GridPillarMatchRule(BaseRule):
#     rule_name = "柱网匹配校验"
#     rule_type = "warning"  # 匹配失败通常是 warning，不是 error
#
#     def __init__(self, grid_pillar_finder=None):
#         """
#         :param grid_pillar_finder: GridPillarFinder 实例
#         :param max_distance: 超过此距离视为“位置异常”（单位：mm 或 DXF 单位）
#         """
#         self.finder = grid_pillar_finder
#
#     def check(self, equipments: List[Equipment]) -> List[CheckResult]:
#         if not self.finder:
#             return []  # 未提供柱网信息，跳过
#
#         # 提取设备坐标
#         device_coords = [(eq.tool_id, eq.insert_point_x, eq.insert_point_y) for eq in equipments]
#
#         # 批量查找最近柱子
#         results = self.finder.find_nearest_for_devices(device_coords)
#
#         check_results = []
#         for eq, res in zip(equipments, results):
#             # 设置 bay_location 为柱子名称
#             #eq.nearest_pillar_name = res["nearest_pillar_name"]
#             (eq.nearest_pillar_x, eq.nearest_pillar_y) = res["coord"]
#             eq.device_coord = res["device_coord"]
#             eq.distance = res["distance"]
#             (eq.grid_x, eq.grid_y) = res["nearest_pillar_name"]
#
#         return results
#
#
# class GridPillarFinder:
#     def __init__(self, field: List[str], XY: List[str], value_from: List[float], value_to: List[float]):
#         """
#         初始化柱子网格
#
#         Args:
#             field: 字段名列表，如 ["2a-01", "2a-02", "A", "B"]
#             XY: 坐标轴标识，如 ["X", "X", "Y", "Y"]
#             value_from: 起始值，如 [0, 7200, 0, 9000]
#             value_to: 结束值（本实现中暂不使用，仅用 value_from 作为柱子位置）
#         """
#         if not (len(field) == len(XY) == len(value_from) == len(value_to)):
#             raise ValueError("所有输入列表长度必须相等")
#
#         # 分离 X 和 Y
#         x_fields = []
#         x_coords = []
#         y_fields = []
#         y_coords = []
#
#         for f, axis, v0, v1 in zip(field, XY, value_from, value_to):
#             if axis == "X":
#                 x_fields.append(f)
#                 x_coords.append(v0)  # 使用 value_from 作为柱子位置
#             elif axis == "Y":
#                 y_fields.append(f)
#                 y_coords.append(v0)
#             else:
#                 raise ValueError(f"XY 列表中只能包含 'X' 或 'Y'，发现: {axis}")
#
#         if not x_fields or not y_fields:
#             raise ValueError("必须同时包含 X 和 Y 定义")
#
#         self.x_fields = x_fields
#         self.y_fields = y_fields
#         self.x_coords = x_coords
#         self.y_coords = y_coords
#
#         # 生成所有柱子（坐标 + 名称）
#         self.pillars = []  # [(name, x, y), ...]
#         for i, x_val in enumerate(x_coords):
#             for j, y_val in enumerate(y_coords):
#                 name = x_fields[i] + y_fields[j]
#                 self.pillars.append((x_fields[i], y_fields[j], x_val, y_val))
#
#         # 构建 KDTree
#         coords_array = np.array([(x, y) for _, _, x, y in self.pillars], dtype=np.float64)
#         self.tree = cKDTree(coords_array)
#         self.pillar_names = [(name_x, name_y) for name_x, name_y, _, _ in self.pillars]
#         self.pillar_coords = coords_array
#
#     def find_nearest_for_devices(self, devices: List[Tuple[str, float, float]]) -> List[Dict]:
#         """
#         为设备列表查找最近的柱子
#
#         Args:
#             devices: [(tool_id1, x1, y1), (tool_id2, x2, y2), ...]
#
#         Returns:
#             List[{
#                 "tool_id": str,
#                 "device_coord": (x, y),
#                 "nearest_pillar_name": str,
#                 "nearest_pillar_coord": (x, y),
#                 "distance": float
#             }]
#         """
#         if not devices:
#             return []
#
#         # 分离 tool_id 和坐标
#         tool_ids = [d[0] for d in devices]
#         device_coords = [(d[1], d[2]) for d in devices]
#
#         device_array = np.array(device_coords, dtype=np.float64)
#         distances, indices = self.tree.query(device_array)
#
#         results = []
#         for i, (tool_id, x, y) in enumerate(devices):
#             idx = indices[i]
#             name = self.pillar_names[idx]
#             coord = tuple(self.pillar_coords[idx])
#             dist = float(distances[i])
#             results.append({
#                 "tool_id": tool_id,  # ← 新增：设备名称
#                 "device_coord": (x, y),  # 原设备坐标
#                 "nearest_pillar_name": name,  # 最近柱子名
#                 "nearest_pillar_coord": coord,  # 柱子坐标
#                 "distance": dist  # 距离
#             })
#         return results
#
#
# # ======================
# # 🧪 使用示例
# # ======================
# if __name__ == "__main__":
#     import random, time
#
#     # 模拟你的数据结构
#     x_fields = [f"X{i:02d}" for i in range(31)]
#     y_fields = [f"Y{j:02d}" for j in range(25)]
#
#     field = x_fields + y_fields
#     XY = ["X"] * 31 + ["Y"] * 25
#     value_from = (
#             [i * 1000 for i in range(31)] +  # X: 0, 1000, ..., 30000
#             [j * 1200 for j in range(25)]  # Y: 0, 1200, ..., 28800
#     )
#     value_to = [v + 1000 for v in value_from]  # 随意生成
#
#     # 4000 个随机设备
#     random.seed(42)
#     devices = [(str(i), random.uniform(0, 30000), random.uniform(0, 28800)) for i in range(4000)]
#
#     # 执行
#     start = time.time()
#     finder = GridPillarFinder(field, XY, value_from, value_to)
#     results = finder.find_nearest_for_devices(devices)
#     elapsed = time.time() - start
#
#     print(f"✅ 柱子: {finder.x_coords[0]}...{finder.x_coords[-1]} × {finder.y_coords[0]}...{finder.y_coords[-1]}")
#     print(f"✅ 柱子总数: {len(finder.pillars)}")
#     print(f"✅ 设备数: {len(devices)}")
#     print(f"⏱️  耗时: {elapsed:.4f} 秒")
#     print(f"🔍 示例: {results}")


# grid_pillar_finder.py
import numpy as np
from scipy.spatial import cKDTree
from typing import List, Tuple, Dict


class GridPillarFinder:
    def __init__(self, field: List[str], XY: List[str], value_from: List[float], value_to: List[float]):
        if not (len(field) == len(XY) == len(value_from) == len(value_to)):
            raise ValueError("所有输入列表长度必须相等")

        x_fields, x_coords, y_fields, y_coords = [], [], [], []
        for f, axis, v0, v1 in zip(field, XY, value_from, value_to):
            if axis == "X":
                x_fields.append(f)
                x_coords.append(v0)
            elif axis == "Y":
                y_fields.append(f)
                y_coords.append(v0)
            else:
                raise ValueError(f"XY 列表中只能包含 'X' 或 'Y'，发现: {axis}")

        if not x_fields or not y_fields:
            raise ValueError("必须同时包含 X 和 Y 定义")

        self.x_fields = x_fields
        self.y_fields = y_fields
        self.x_coords = x_coords
        self.y_coords = y_coords

        # 生成所有柱子
        self.pillars = [(xf, yf, x, y) for xf, x in zip(x_fields, x_coords) for yf, y in zip(y_fields, y_coords)]

        coords_array = np.array([(x, y) for _, _, x, y in self.pillars], dtype=np.float64)
        self.tree = cKDTree(coords_array)
        self.pillar_names = [(name_x, name_y) for name_x, name_y, _, _ in self.pillars]
        self.pillar_coords = coords_array

    def find_nearest_for_devices(self, devices: List[Tuple[str, str, float, float]]) -> List[Dict]:
        if not devices:
            return []

        tool_ids = [d[0] for d in devices]
        device_coords = [(d[1], d[2]) for d in devices]

        device_array = np.array(device_coords, dtype=np.float64)
        distances, indices = self.tree.query(device_array)

        results = []
        for i, (tool_id, x, y) in enumerate(devices):
            idx = indices[i]
            results.append({
                "tool_id": tool_id,
                "device_coord": (x, y),
                "nearest_pillar_name": self.pillar_names[idx],
                "nearest_pillar_coord": tuple(self.pillar_coords[idx]),
                "distance": float(distances[i])
            })
        return results

from typing import List, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_rules import BaseRule
from app.fid.models import Equipment, CheckResult

import datetime

class GridSearcher:
    def __init__(self, rules: List[BaseRule]):
        self.rules = rules

    def validate(self, equipments: List[Equipment], check_info: Any) -> List[CheckResult]:
        start_time = datetime.datetime.now()
        results = []
        for rule in self.rules:
            results.extend(rule.check(equipments, check_info))

        print(f"柱网匹配耗时 {datetime.datetime.now() - start_time}")
        return results
