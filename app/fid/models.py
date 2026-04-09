from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass

@dataclass
class FileInfo:
    filename: str
    company: str
    building_id: str
    building_level: str
    fab_id: str
    id_: str
    owner2id: Dict[str, str]

@dataclass
class Equipment:
    # 业务属性
    tool_id: Optional[str]

    id: Any = None
    fab_id: Any = None
    building_id: Any = None
    building_level: Any = None
    group_id: Any = None


    owner: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    process: Optional[str] = None
    grid_x: float = None
    grid_y: float = None
    locked: Optional[str] = None
    bay_location: Optional[str] = None
    record: Optional[str] = None

    # 固有属性
    cad_block_name: str = ""
    layer: str = ""
    angle: float = 0.0
    true_color: int = 0
    insert_point_x: float = 0.0
    insert_point_y: float = 0.0
    insert_point_z: float = 0.0
    center_point_x: float = 0.0
    center_point_y: float = 0.0
    cad_block_id: str = ""

    file_info: Optional[FileInfo] = None

    operation: Optional[str] = ""# "add", "update", "delete"
    grid_name: Optional[str] = ""


    device_coord: any = None
    distance: any = None

    errors: List[Dict[str, str]] = None

    is_virtual_eqp: int = 0 #isVirtualEqp


@dataclass
class CheckResult:
    type: str  # "error" or "warning"
    name: str
    description: str
    detail: Dict[str, Any]
    operation: str = None
    field_or_interface: str = None
    equipment: Optional[Equipment] = None
    errors: Any = None,
    device: str = None
