import math
import numpy as np
from typing import Any

def replace_nan_with_none(obj: Any) -> Any:
    """
    递归遍历 dict/list，将 NaN/Inf 等非法浮点值替换为 None
    """
    if isinstance(obj, dict):
        return {k: replace_nan_with_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_with_none(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    elif isinstance(obj, (np.floating, np.integer)):
        # 处理 numpy 标量（如 np.float64, np.int32）
        if np.isnan(obj) or np.isinf(obj):
            return None
        # 可选：将 numpy 类型转为 Python 原生类型（避免后续 JSON 序列化问题）
        return obj.item()  # 转为 int / float
    elif obj is np.nan:  # 显式检查 np.nan（虽然通常被 float 捕获）
        return None
    return obj
