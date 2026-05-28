
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import ezdxf
from ezdxf import bbox

from app.sld.models import SldDevice


def parse_sld_dxf(
    dxf_path: str | Path,
    target_layers: Optional[Sequence[str]] = None,
    *,
    bbox_fast: bool = True,
) -> List[SldDevice]:
    path = Path(dxf_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))

    tl_set: Optional[set[str]] = None
    if target_layers is not None:
        tl_set = {str(x).strip() for x in target_layers if str(x).strip()}

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    rows: List[SldDevice] = []
    print(msp)
    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue
            
        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            continue


        bb = bbox.extents([entity], fast=bbox_fast)
        if bb is not None:
            center_x = (bb.extmin.x + bb.extmax.x) / 2
            center_y = (bb.extmin.y + bb.extmax.y) / 2
        else:
            center_x = entity.dxf.insert.x
            center_y = entity.dxf.insert.y
        print(f"**************************")
        print(center_x)
        print(center_y)

        print(f"**************************")
        print(doc.blocks)
        print(entity.dxf.name)
        attrs: Dict[str, str] = {}
        for attr in entity.attribs:

            if (hasattr(attr, "dxf") and hasattr(attr.dxf, "tag")) and hasattr(attr.dxf, "text"):
                print(f"**************************")
                print(attr.dxf.tag)
                print(attr.dxf.text)
                print(attr.dxf)
                print(f"**************************")
                attrs[attr.dxf.tag] = attr.dxf.text
        print(attrs)
        print(f"**************************")



if __name__ == "__main__":
    dxf_path = "app/sld/doc/YMTC^SLD^FAB1^F1.dxf"
    target_layers = []
    bbox_fast = True
    devices = parse_sld_dxf(dxf_path, target_layers, bbox_fast=bbox_fast)
    # print(devices)