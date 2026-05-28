from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SldDevice:
    """SLD 单条设备（图面 INSERT 解析结果 + 柱网 enrichment）。"""

    id_equ: Optional[str] = None
    id_equ_sub_short: Optional[str] = None
    tool_id: Optional[str] = None

    owner: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    bay_location: Optional[str] = None
    records: Optional[str] = None

    grid_x: Optional[str] = None
    grid_y: Optional[str] = None

    block_name: str = ""
    layer: str = ""
    angle: float = 0.0
    true_color: int = 0
    insert_point_x: float = 0.0
    insert_point_y: float = 0.0
    insert_point_z: float = 0.0
    center_point_x: float = 0.0
    center_point_y: float = 0.0
    center_point_z: float = 0.0
    block_id: str = ""

    # 与上一版对比的变更标记：None / "add" / "update" / "delete"
    operation: Optional[str] = None

    # 与 eldSubEquipmentList / equipmentList 匹配到的原始行，仅用于 API 回带 id 等数据库字段
    eld_source_row: Optional[Dict[str, Any]] = None
    equipment_source_row: Optional[Dict[str, Any]] = None

    raw_attrib_tags: List[str] = field(default_factory=list)


@dataclass
class SldIssue:
    """单条校验问题（后续可聚合为 API 的 error / warning 分组）。"""

    type: str  # "error" | "warning"
    name: str
    description: str
    detail: Dict[str, Any] = field(default_factory=dict)
    device: Optional[SldDevice] = None


@dataclass
class SldFileContext:
    """一次校验任务的上下文（文件名、允许的 OWNER 等）。"""

    file_path: str
    filename_stem: str
    company_token: str
    building_token: str
    level_token: str
    allowed_owner_codes: frozenset[str]
    efms_equipment_codes: frozenset[str] = frozenset()
