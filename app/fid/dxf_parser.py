# dxf_parser.py
import json
import time

import ezdxf
from ezdxf import bbox
from typing import List
from app.fid.models import Equipment, FileInfo

import datetime
import traceback


def parse_dxf(dxf_path, file_info: FileInfo = None, target_layers=None) -> List[Equipment]:
    """
    解析 DXF 文件，提取所有包含 'TOOL_ID' 属性的 INSERT 块（设备）。

    :param dxf_path: DXF 文件路径
    :param file_info: 文件信息（用于绑定到 Equipment）
    :return: Equipment 列表
    """
    start_time = datetime.datetime.now()

    if target_layers:
        target_layers = [tl['code'] for tl in target_layers]

    try:
        print(f"{dxf_path=} {type(dxf_path)}")
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        print(traceback.format_exc())
        raise Exception(f'dxf解析失败: {str(e)}')

    msp = doc.modelspace()
    equipments: List[Equipment] = []

    owerlist = []
    for entity in msp:

        # 只处理 INSERT（块引用）
        if entity.dxftype() != "INSERT":
            continue

        if target_layers and str(entity.dxf.layer) not in target_layers:
            print(f"{str(entity.dxf.layer)} 不在目标layers中 {target_layers}")
            continue

        # 获取块定义（用于检查是否含属性）
        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            continue

        block = doc.blocks[block_name]
        # print(f"{block_name=}")

        try:
            # 获取块的包围盒（考虑旋转、缩放）
            bb = bbox.extents([entity], fast=False)  # fast=False 更准确
            if bb is not None:
                center_x = (bb.extmin.x + bb.extmax.x) / 2
                center_y = (bb.extmin.y + bb.extmax.y) / 2
            else:
                # 退回到插入点
                center_x = entity.dxf.insert.x
                center_y = entity.dxf.insert.y
        except Exception as e:
            # 如果计算失败，用插入点
            center_x = entity.dxf.insert.x
            center_y = entity.dxf.insert.y

        # 提取所有属性（ATTRIB）
        attrs = {}
        for attr in entity.attribs:
            if hasattr(attr, 'dxf') and hasattr(attr.dxf, 'tag') and hasattr(attr.dxf, 'text'):
                tag = str(attr.dxf.tag).strip().upper()
                text = str(attr.dxf.text).strip() if attr.dxf.text else ''
                attrs[tag] = text
        # 只处理包含 TOOL_ID 的块
        if "TOOL_ID" not in attrs or not attrs["TOOL_ID"]:
            print('缺少TOOL_ID, 跳过！')
            continue
        else:
            # tool_id 删除开头的^
            attrs['TOOL_ID'] = attrs['TOOL_ID'][1:].strip() if attrs['TOOL_ID'] and attrs['TOOL_ID'].startswith(
                '^') else attrs['TOOL_ID'].strip()

        # if attrs.get("TOOL_ID", None) not in ['OPC', 'AOLUS03']:
        #     continue
        # print(attrs)
        # continue
        # if attrs.get("OWNER", None) not in owerlist:
        #     owerlist.append(attrs.get("OWNER", None))
        #     print(f"{owerlist=}")

        # 构建 Equipment 对象
        owner_code = (attrs.get("OWNER", '') or attrs.get("EQU.GROUP", '')).upper()
        group_id = file_info.owner2id.get(owner_code) if file_info is not None and owner_code != '' else None
        # print(f"{owner_code=} {group_id=}")
        eq = Equipment(
            id=file_info.id_ if file_info != None else None,
            fab_id=file_info.fab_id if file_info != None else None,
            building_id=file_info.building_id if file_info != None else None,
            building_level=file_info.building_level if file_info != None else None,
            group_id=group_id,
            tool_id=attrs.get("TOOL_ID", None),
            owner=attrs.get("OWNER", None) or attrs.get("EQU.GROUP", None),
            vendor=attrs.get("VENDOR", None),
            model=attrs.get("MODEL", None),
            bay_location=attrs.get("BAY_LOCATION", None),
            record=attrs.get("RECORDS", None),
            # 固有属性
            cad_block_name=block_name,
            layer=entity.dxf.layer,
            angle=float(entity.dxf.rotation) if hasattr(entity.dxf, 'rotation') else 0.0,
            true_color=int(entity.dxf.color) if hasattr(entity.dxf, 'color') else 0,
            insert_point_x=round(float(entity.dxf.insert.x), 4),
            insert_point_y=round(float(entity.dxf.insert.y), 4),
            insert_point_z=round(float(entity.dxf.insert.z), 4),
            center_point_x=round(float(center_x), 4),
            center_point_y=round(float(center_y), 4),

            cad_block_id=str(entity.dxf.handle),
            file_info=file_info,
        )
        if eq.group_id is None:
            print(f"file_info is None -> {file_info is None}")
            print(f"{attrs.get('OWNER')=} {owner_code=}")
            # print(json.dumps(file_info.owner2id, ensure_ascii=False, indent=2))

        equipments.append(eq)
    print(f"共解析出 {len(equipments)} 节点")
    print(f"解析文件耗时： {datetime.datetime.now() - start_time}")
    return equipments


if __name__ == '__main__':
    parse_dxf("v:/Desktop/eld_check/YMTC^ELD^FAB1^F3.dxf")
