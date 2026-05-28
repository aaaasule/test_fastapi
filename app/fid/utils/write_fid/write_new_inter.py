"""新版插接口 NEW_INTER_：写入属性 EQU。"""


def write_new_inter_equipment_code(attrs_by_tag: dict, equipment_code: str) -> bool:
    target_attr = attrs_by_tag.get("EQU")
    if target_attr is None:
        return False
    target_attr.dxf.text = equipment_code
    return True
