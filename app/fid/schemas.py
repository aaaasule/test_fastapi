from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# 所有模型统一使用 camelCase 别名 + snake_case 内部字段
class BaseModelCamel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,   # 允许用 snake_case 赋值（方便测试/内部调用）
        extra="allow"
    )

# 注意：所有嵌套模型也必须继承 BaseModel（不能是 dataclass）

class EquipmentItem(BaseModelCamel):

    id: Any
    fab_id: Any
    building_id: Any
    building_level: Any
    group_id: Any

    code: str = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    process: Optional[str] = None
    grid_x: Optional[str] = None
    grid_y: Optional[str] = None
    locked: Optional[str] = None
    bay_location: Optional[str] = None
    record: Optional[str] = None

    cad_block_name: Optional[str] = None
    layer: Optional[str] = None
    angle: Optional[float] = None
    true_color: Optional[int] = None
    insert_point_x: Optional[float] = None
    insert_point_y: Optional[float] = None
    insert_point_z: Optional[float] = None
    center_point_x: Optional[float] = None
    center_point_y: Optional[float] = None
    cad_block_id: Optional[str] = None

    errors: Any
    operation: Any  # "add", "update", "delete"
    description: str = None
    is_virtual_eqp: int = 0
    diff_content: List[str] = Field(default_factory=list)


class FidEquipmentItem(BaseModelCamel):

    id: Any
    parent_id: str
    field_id: Any
    building_id: Any
    building_level: Any
    uni_code: Any

    code: str = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    process: Optional[str] = None
    grid_x: Optional[str] = None
    grid_y: Optional[str] = None
    locked: Optional[str] = None
    bay_location: Optional[str] = None
    record: Optional[str] = None

    cad_block_name: Optional[str] = None
    layer: Optional[str] = None
    angle: Optional[float] = None
    true_color: Optional[int] = None
    insert_point_x: Optional[float] = None
    insert_point_y: Optional[float] = None
    insert_point_z: Optional[float] = None
    center_point_x: Optional[float] = None
    center_point_y: Optional[float] = None
    cad_block_id: Optional[str] = None

    errors: Any
    operation: Any  # "add", "update", "delete"


class GridInfo(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    Field: List[str] = []  # 对应 JSON 中的 "field"
    XY: List[str] = []
    Value_From: List[float] = []
    Value_To: List[float] = []


class CheckerInfo(BaseModelCamel):
    layer_list: List[str] = []
    equipment_group_list: List[str] = []
    grid_info: GridInfo


class CheckItem(BaseModelCamel):
    col1: str
    col2: str


class CheckError(BaseModelCamel):
    name: str
    type: str
    description: str
    items: List[Dict[str, Any]] = []


class ELDCheckRequest(BaseModelCamel):
    file: str
    company: str
    fab: str
    building: str
    level: str
    eqp_data: List[EquipmentItem] = []
    checker_info: CheckerInfo


class ELDCheckResponse(BaseModelCamel):
    code: int
    message: str
    error: List[CheckError] = []
    warning: List[CheckError] = []
    data: List[EquipmentItem] = []


class WriteFidInterfaceDetail(BaseModelCamel):
    id: Any
    parent_id: Optional[Any] = None
    field_id: Optional[Any] = None

    code: Optional[str] = None
    uni_code: Optional[str] = None
    building_id: Optional[Any] = None
    building_level: Optional[str] = None
    distribution_box: Optional[Literal[0, 1]] = None
    con_size: Optional[str] = None
    con_type: Optional[str] = None
    max_design_flow: Optional[str] = None
    in_out_code: Optional[str] = None
    peak: Optional[str] = None
    oper: Optional[str] = None
    ave: Optional[str] = None
    unit: Optional[str] = None

    cad_block_name: Optional[str] = None
    cad_block_id: Optional[str] = None
    layer: Optional[str] = None
    insert_point_x: Optional[float] = None
    insert_point_y: Optional[float] = None
    insert_point_z: Optional[float] = None
    angle: Optional[float] = None
    true_color: Optional[int] = None

    is_assigned: Optional[Literal[0, 1, 2, 3]] = None
    status: Optional[Literal["add", "update", "delete"]] = None
    locked: Optional[Literal[0, 1]] = None
    lock_user_id: Optional[str] = None
    tee_off_flag: Optional[Literal[0, 1]] = None
    remark: Optional[str] = None
    is_virtual: Optional[Literal[0, 1]] = None

    equipment_code: Optional[str] = None
    system_code: Optional[str] = None
    tee_list: List[Dict[str, Any]] = Field(default_factory=list)


class WriteFidRequest(BaseModelCamel):
    interfacesDetailList: List[WriteFidInterfaceDetail] = Field(..., min_length=1)
    filePath: str = Field(..., min_length=1)
    local_dxf_path: Optional[str] = None


class WriteFidResponse(BaseModelCamel):
    code: int
    message: str
    success: bool
    data: str = ""
