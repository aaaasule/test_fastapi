"""TakeOff：定位键与图块 INTERFACE_CODE 对齐入参 uniCode / code。"""

from typing import Dict, List

from . import common


def locator_keys_takeoff(attrs: Dict[str, str]) -> List[str]:
    ic = common.strip(attrs.get("INTERFACE_CODE"))
    return [ic] if ic else []
