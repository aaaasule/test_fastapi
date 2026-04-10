# 导入所有规则（便于集中管理）
from app.fid.validators.rules.required_field_rule import RequiredFieldRule
from app.fid.validators.rules.tool_id_format_rule import ToolIdFormatRule
from app.fid.validators.rules.uniqueness_rule import UniquenessRule
from app.fid.validators.rules.filename_format_rule import FilenameFormatRule
from app.fid.validators.rules.change_add_rule import EquipmentAddRule
from app.fid.validators.rules.change_delete_rule import EquipmentDeleteRule
from app.fid.validators.rules.change_update_rule import EquipmentUpdateRule
from app.fid.validators.rules.OwnerInEquipmentGroupRule import ValidateEquipmentOwner


from app.fid.validators.change_validator import ELDChangeValidator
from app.fid.validators.filename_validator import DXFFilenameValidator
from app.fid.validators.rule_validator import ELDRuleValidator, FIDRuleValidator, FIDDeleteValidator

from app.fid.validators.grid_pillar_finder import GridPillarFinder, GridSearcher
from app.fid.validators.rules.grid_pillar_match_rule import GridPillarMatchRule
# ... 其他规则

# 默认启用的规则（可通过配置文件覆盖）
DEFAULT_RULE_RULES = [
    RequiredFieldRule(),
    #ToolIdFormatRule(),
    #UniquenessRule(),
    ValidateEquipmentOwner()
    #GridPillarMatchRule()
    # EquipmentGroupRule(),  # 未来新增
]

DEFAULT_FILENAME_RULES = [
    #FilenameFormatRule(),
]

DEFAULT_CHANGE_RULES = [
    EquipmentAddRule(),
    EquipmentDeleteRule(),
    EquipmentUpdateRule(),
    UniquenessRule()
    # AttributeChangeRule(),
    # PositionChangeRule(),
]

DEFAULT_EXCEL_RULES = [
    ValidateEquipmentOwner(),
    RequiredFieldRule()
]
EXCEL_CHANGE_RULES = [
    UniquenessRule()
]

from app.fid.validators.fid_rules.block_added import BlockAddCheck
from app.fid.validators.fid_rules.block_attribute_modified import BlockAttributeCheck
from app.fid.validators.fid_rules.block_position_changed import BlockPositionCheck
from app.fid.validators.fid_rules.block_removed import BlockRemovedCheck
from app.fid.validators.fid_rules.building_level_check import BuildingLevelCheck
from app.fid.validators.fid_rules.fid_required_field import FidRequiredFieldRule
from app.fid.validators.fid_rules.fid_uniqueness_rule import FidUniqueCheck
from app.fid.validators.fid_rules.idx_unique_check import IdxUniqueCheck
from app.fid.validators.fid_rules.interface_added import InterfaceAddCheck
from app.fid.validators.fid_rules.interface_removed import InterfaceRemoveCheck
from app.fid.validators.fid_rules.interfacecode_check import FIDInterfaceCodeRule
from app.fid.validators.fid_rules.subsystem_check import SubsystemCheck
from app.fid.validators.fid_rules.takeoff_check import TakeoffCSCTCheck
from app.fid.validators.fid_rules.vmb_slurry_check import VMBSlurryCheck
from app.fid.validators.fid_rules.vmb_idchemical_mismatch import VMBIdChemicalCheck

DEFAULT_FID_RULE_RULES = {
    "TAKEOFF": [
        BlockAttributeCheck(),
        BlockPositionCheck(),
        BlockAddCheck(),
        #BlockRemovedCheck(),
        InterfaceAddCheck(),
        #InterfaceRemoveCheck(),


        FidRequiredFieldRule(),
        FIDInterfaceCodeRule(),
        SubsystemCheck(),
        BuildingLevelCheck(),
        TakeoffCSCTCheck(),
        FidUniqueCheck()
    ],
    "VMB_CHEMICAL": [
        BlockAttributeCheck(),
        BlockPositionCheck(),
        BlockAddCheck(),
        #BlockRemovedCheck(),
        InterfaceAddCheck(),
        #InterfaceRemoveCheck(),


        FidRequiredFieldRule(),
        FIDInterfaceCodeRule(),
        SubsystemCheck(),
        BuildingLevelCheck(),
        TakeoffCSCTCheck(),
        IdxUniqueCheck(),
        FidUniqueCheck(),


        VMBSlurryCheck(),
        VMBIdChemicalCheck(),

    ],
    "VMB_GASNAME": [
        BlockAttributeCheck(),
        BlockPositionCheck(),
        BlockAddCheck(),
        #BlockRemovedCheck(),
        InterfaceAddCheck(),
        #InterfaceRemoveCheck(),


        FidRequiredFieldRule(),
        FIDInterfaceCodeRule(),
        SubsystemCheck(),
        BuildingLevelCheck(),
        TakeoffCSCTCheck(),
        IdxUniqueCheck(),
        FidUniqueCheck(),


        VMBSlurryCheck(),
        VMBIdChemicalCheck(),
    ],
    "GPB": [
        BlockAttributeCheck(),
        BlockPositionCheck(),


        BlockAddCheck(),
        #BlockRemovedCheck(),
        InterfaceAddCheck(),
        #InterfaceRemoveCheck(),

        FidRequiredFieldRule(),
        FIDInterfaceCodeRule(),
        SubsystemCheck(),
        BuildingLevelCheck(),

        IdxUniqueCheck(),
        FidUniqueCheck(),

    ],
    "I_LINE": [
        BlockAttributeCheck(),
        BlockPositionCheck(),

        BlockAddCheck(),
        #BlockRemovedCheck(),
        InterfaceAddCheck(),
        #InterfaceRemoveCheck(),

        FidRequiredFieldRule(),
        FIDInterfaceCodeRule(),
        SubsystemCheck(),
        BuildingLevelCheck(),

        IdxUniqueCheck(),
        FidUniqueCheck(),
    ],
    "NEW_INTER_": [
        BlockAttributeCheck(),
        BlockPositionCheck(),

        BlockAddCheck(),
        #BlockRemovedCheck(),
        InterfaceAddCheck(),
        #InterfaceRemoveCheck(),

        FidRequiredFieldRule(),
        FIDInterfaceCodeRule(),
        SubsystemCheck(),
        BuildingLevelCheck(),

        FidUniqueCheck(),
    ],
}

FID_DELETE_RULES = {
    BlockRemovedCheck(),
    InterfaceRemoveCheck()
}
