"""VMB / Slurry：定位键为「ID + '-' + ID.x 值」与入参 uniCode / code 一致。"""

from typing import Dict, List, Set

from . import common


def vmb_compound_locator_key(id_main: str, port_val: str) -> str:
    """图块 ID 与 ID.x 端口值组成定位键，与入参 uniCode（如 …;07-R2）对齐。"""
    id_main = common.strip(id_main)
    vx = common.strip(port_val)
    if not vx:
        return ""
    if id_main:
        return f"{id_main}-{vx}"
    return vx


def vmb_port_compounds_casefold(attrs: Dict[str, str]) -> Set[str]:
    """从图块属性收集所有端口定位键（小写），用于多分支接口行关联。"""
    out: Set[str] = set()
    for _, vx in common.id_dot_entries(attrs):
        key = vmb_compound_locator_key(common.strip(attrs.get("ID")), vx)
        if key:
            out.add(key.casefold())
    return out


def locator_keys_vmb_slurry(attrs: Dict[str, str]) -> List[str]:
    id_main = common.strip(attrs.get("ID"))
    dots = common.id_dot_entries(attrs)
    keys: List[str] = []
    for _, vx in dots:
        key = vmb_compound_locator_key(id_main, vx)
        if key:
            keys.append(key)
    if id_main and not keys:
        keys.append(id_main)
    return common.dedupe_keys(keys)
