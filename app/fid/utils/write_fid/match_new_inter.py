"""新版插接口 NEW_INTER_：uniCode 第三段对齐 ID_SHORT，回填写属性 EQU。"""

from typing import Dict, List, Optional

from . import common
from .match_context import WriteFidMatchContext


def match_new_inter_equipment_code(
    attrs: Dict[str, str],
    interfaces: Optional[List[dict]] = None,
    match_ctx: Optional[WriteFidMatchContext] = None,
) -> str:
    id_short = common.strip(attrs.get("ID_SHORT"))
    if not id_short:
        return ""

    items: List[dict] = []
    if match_ctx is not None:
        items = list(match_ctx.items_by_id_short.get(id_short, []))
    elif interfaces:
        items = interfaces

    for item in items:
        if not common.interface_is_assigned(item):
            continue
        ec = common.strip(item.get("equipmentCode"))
        if not ec:
            continue
        for field in ("uniCode", "code"):
            uc = common.strip(item.get(field))
            if not uc:
                continue
            parts = [p.strip() for p in uc.split(";")]
            if len(parts) < 3:
                continue
            if parts[2] != id_short:
                continue
            return ec
    return ""
