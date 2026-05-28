# SLD 模块内建常量（不依赖 app.fid）

# ID_EQU 规范性：与业务约定一致时可调整；此处为占位，与常见 TOOL_ID 规则类似
ID_EQU_PATTERN = r"^[A-Z].*\d{2}$"

# 判定「位置变更」的平面距离阈值（DXF 图纸单位，通常为 mm）
POSITION_CHANGE_EPSILON = 1.0

# 大图纸：包围盒使用 fast 模式（更快，精度略低）
DEFAULT_BBOX_FAST = True
