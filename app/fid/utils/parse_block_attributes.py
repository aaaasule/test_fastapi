import json
import sys
from pathlib import Path
current_file = Path(__file__).resolve()
root_dir = current_file.parent
while root_dir.name != 'app' and root_dir.parent != root_dir:
    root_dir = root_dir.parent

if root_dir.name == 'app':
    project_root = root_dir.parent
else:
    #  fallback: 假设就在上一级
    project_root = current_file.parent.parent

# 3. 将项目根目录加入 Python 搜索路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from app.fid.utils.check_device import check_which_device

import traceback
from typing import List, Any, Dict
import re

def parse_interface_code(code: str) -> dict:
    if not isinstance(code, str):
        code = str(code)

    parts = code.split(';', 3)  # 最多分割3次 → 得到最多4个部分

    # 确保有4个元素，不足则补空字符串
    while len(parts) < 4:
        parts.append('')

    return {
        'sub_system': parts[0],
        'building_level': parts[1],
        'field': parts[2],
        'id': parts[3]
    }


def parse_block_attributes(equipment, filename):
    try:
        # print('[parse_block_attributes] device -',check_which_device(equipment, filename))

        final_result = [{
            "id": '',
            "building_level": '',
            "field": '',
            "system": '',
            "sub_system": '',
            'field_code': '',
            'field_check_code': '',
            "interface_code": '',
            "search_id": '',
            "connection_size": '',
            "connection_type": '',
            "equipment_code": '',
            "flow_unit": '',
            "design_flow": '',
            "cad_block_name": '',
            "layer": '',
            "insert_point_x": '',
            "insert_point_y": '',
            "insert_point_z": '',
            "angle": '',
            "true_color": '',
            "cad_block_id": '',
            "distribution_box": ''
        }]
        result = []

        #print(f"[parse_block_attributes.py]{equipment=}")
        equipment = {k.upper():v for k,v in equipment.items()}
        if check_which_device(equipment, filename) is None or 'UNI_CODE' in equipment:
            return final_result

        if check_which_device(equipment, filename) == 'TAKEOFF':
            name = str(equipment['INTERFACE_CODE'] or '')
            try:

                sub_system, building_level, field, id_ = name.split(';', 3)
                # print(f"{sub_system=} {building_level=} {field=} {id_=}")
                code = parse_interface_code(name)
                sub_system, building_level, field, id_ = code.get('sub_system'), code.get('building_level'), code.get(
                    'field'), code.get('id')
                # print(f"{sub_system=} {building_level=} {field=} {id_=}")
            except:
                sub_system, building_level, field, id_ = '', '', '', ''
            result = [{
                "id": id_,
                "building_level": building_level,
                "field": field,
                "system": "PA",
                "sub_system": sub_system,
                'field_code': f'{sub_system}.{building_level}.{field}',
                #'field_check_code': f'{sub_system};{building_level};{field}',
                "interface_code": name,
                "search_id": name,
                "connection_size": equipment.get('CS', ''),
                "connection_type": equipment.get('CT', ''),
                "equipment_code": equipment.get('EQUIPMENT_CODE', ''),
                "flow_unit": equipment.get('FLOW_UNIT', ''),
                "design_flow": equipment.get('DESIGN_FLOW', ''),
                "cad_block_name": equipment['CAD_BLOCK_NAME'],
                "layer": equipment['LAYER'],
                "insert_point_x": equipment['INSERT_POINT_X'],
                "insert_point_y": equipment['INSERT_POINT_Y'],
                "insert_point_z": equipment['INSERT_POINT_Z'],
                "angle": equipment['ANGLE'],
                "true_color": equipment['TRUE_COLOR'],
                "cad_block_id": equipment['CAD_BLOCK_ID'],
                "distribution_box": False
            }]

        elif check_which_device(equipment, filename).startswith('VMB'):

            result = []

            name = str(equipment['ID'] or '')
            try:
                # sub_system, building_level, field = name.split(';', 2)
                code = parse_interface_code(name)
                sub_system, building_level, field, id_ = code.get('sub_system'), code.get('building_level'), code.get(
                    'field'), code.get('id')
                if len(id_) > 0:
                    field = f"{field};{id_}"

            except:
                print(traceback.format_exc())
                sub_system, building_level, field = '', '', ''

            all_interface_set = set()
            for k, v in equipment.items():
                # if '.' in k and k.endswith(('DESIGN_FLOW', 'FLOW_UNIT')):
                #     _k = k.split('.')[0]
                #     if _k not in all_interface_set:
                #         all_interface_set.add(_k)
                # elif '.' in k and k.startswith(('EQU', 'ID', 'CS', 'CT', 'I/O')) and k not in ['ID_SHORT']:
                #     _k = k.split('.')[-1]
                #     if _k not in all_interface_set:
                #         all_interface_set.add(_k)

                if '.' in k and k.startswith('ID') and k not in ['ID_SHORT']:
                    _k = k.split('.')[-1]
                    if _k not in all_interface_set:
                        all_interface_set.add(_k)

            #print(f"{all_interface_set=}")
            if len(all_interface_set) == 0:
                print(f'没有接口，没识别到任何信息:{equipment=}')

            for _id in all_interface_set:
                IDx = equipment.get(f'ID.{_id}')
                _result = {
                    "vmb-type": equipment.get('VMB-TYPE') or equipment.get('GC-TYPE'),
                    "building_level": building_level,
                    "field": field,
                    "system": "PC",
                    "sub_system": sub_system,
                    "field_code": f"{sub_system}.{building_level}.{field}",
                    #"field_code": name,
                    "interface_code": f"{equipment.get('ID') or ''}-{IDx}" if IDx not in [None, ''] else f"{equipment.get('ID') or ''}-{_id}",
                    "search_id": f"{sub_system};{building_level};{field}",
                    'id': f"{IDx or ''}" if IDx != None else f"{_id or ''}",
                    "connection_size": equipment.get(f'CS.{_id}', ''),
                    "connection_type": equipment.get(f'CT.{_id}', ''),
                    "equipment_code": equipment.get(f'EQU.{_id}', ''),
                    "I/O": equipment.get(f'I/O.{_id}'),
                    'x': _id,
                    "IDx": IDx,
                    "flow_unit": equipment.get(f'{_id}.FLOW_UNIT', ''),
                    "design_flow": equipment.get(f'{_id}.DESIGN_FLOW', ''),
                    "cad_block_name": equipment['CAD_BLOCK_NAME'],
                    "layer": equipment['LAYER'],
                    "insert_point_x": equipment['INSERT_POINT_X'],
                    "insert_point_y": equipment['INSERT_POINT_Y'],
                    "insert_point_z": equipment['INSERT_POINT_Z'],
                    "angle": equipment['ANGLE'],
                    "true_color": equipment['TRUE_COLOR'],
                    "cad_block_id": equipment['CAD_BLOCK_ID'],
                    "distribution_box": True
                }
                # print(f"{_id=}")
                # print(f"{equipment.get('ID') or ''}-{IDx}")
                # print(IDx is not None)
                # print(f"{equipment.get('ID') or ''}-{_id}")
                # print('[parser block]interfacecode-', '|', f"{equipment.get('ID') or ''}", '|', IDx is not None, '|',
                #       f"{equipment.get('ID', '')}-{IDx}", '|', f"{equipment.get('ID', '')}-{_id}")
                # print(f"{equipment=}")
                # print('-' * 100)
                if 'CHEMICALNAME' in equipment:
                    _result['chemical_name'] = equipment.get('CHEMICALNAME')
                else:
                    _result['gas_name'] = equipment.get('GASNAME')
                result.append(_result)


        elif check_which_device(equipment, filename) in ['I_LINE', 'GPB']:

            result = []
            name = str(equipment['ID'] or '')
            try:
                # sub_system, building_level, field = name.split(';', 2)
                code = parse_interface_code(name)
                sub_system, building_level, field, id_ = code.get('sub_system'), code.get('building_level'), code.get(
                    'field'), code.get('id')
                if len(id_) > 0:
                    field = f"{field};{id_}"
            except:
                sub_system, building_level, field = '', '', ''

            all_interface_set = set()
            for k, v in equipment.items():
                # if '.' in k and k.endswith(('DESIGN_FLOW', 'FLOW_UNIT')):
                #     _k = k.split('.')[0]
                #     if _k not in all_interface_set:
                #         all_interface_set.add(_k)
                # elif '.' in k and k.startswith(('EQU', 'ID', 'CS', 'CT', 'I/O')) and k not in ['ID_SHORT']:
                #     _k = k.split('.')[-1]
                #     if _k not in all_interface_set:
                #         all_interface_set.add(_k)
                if '.' in k and k.startswith('ID') and k not in ['ID_SHORT']:
                    _k = k.split('.')[-1]
                    if _k not in all_interface_set:
                        all_interface_set.add(_k)

            # PS、PC and distribution=True 带横杠  interface   sub_system;buildinglevel;
            # field_code: field
            # field_unicode  ; 变成.    sub_system.buildinglevel.field

            # interface 拼的是unicode
            # code  interface最后一个 - 或者 ; 后面的

            for _id in all_interface_set:
                IDx = equipment.get(f'ID.{_id}')
                # print(f"{IDx=} {_id=}")
                _result = {
                    "building_level": building_level,
                    "field": equipment.get('ID_SHORT'),
                    "system": "PC",
                    "sub_system": sub_system,
                    "interface_code": f"{sub_system};{building_level};{equipment.get('ID_SHORT') or ''};{IDx}" if IDx not in [None, ''] else f"{sub_system};{building_level};{equipment.get('ID_SHORT') or ''};{_id}",
                    'id': f"{IDx}" if IDx != None else f"{_id}",
                    "field_code": f"{sub_system}.{building_level}.{equipment.get('ID_SHORT')}",
                    "search_id": equipment.get('ID_SHORT') or '',
                    "connection_size": equipment.get(f'CS.{_id}', ''),
                    "connection_type": equipment.get(f'CT.{_id}', ''),
                    "equipment_code": equipment.get(f'EQU.{_id}', ''),
                    "cad_block_name": equipment['CAD_BLOCK_NAME'],
                    "layer": equipment['LAYER'],
                    "insert_point_x": equipment['INSERT_POINT_X'],
                    "insert_point_y": equipment['INSERT_POINT_Y'],
                    "insert_point_z": equipment['INSERT_POINT_Z'],
                    "angle": equipment['ANGLE'],
                    "true_color": equipment['TRUE_COLOR'],
                    "cad_block_id": equipment['CAD_BLOCK_ID'],
                    "distribution_box": True
                }

                result.append(_result)
        elif check_which_device(equipment, filename) == 'NEW_INTER_':  # 新接口
            # print(check_which_device(equipment), equipment)
            result = []
            name = str(equipment['ID'] or '')
            try:
                # sub_system, building_level, _ = name.split(';', 2)
                code = parse_interface_code(name)
                sub_system, building_level, field, id_ = code.get('sub_system'), code.get('building_level'), code.get(
                    'field'), code.get('id')

            except:
                sub_system, building_level, _ = '', '', ''

            field = (equipment.get('ID_SHORT') or '').split(';')[0]

            all_interface_set = set()
            for k, v in equipment.items():
                # if '.' in k and k.endswith(('DESIGN_FLOW', 'FLOW_UNIT')):
                #     _k = k.split('.')[0]
                #     if _k not in all_interface_set:
                #         all_interface_set.add(_k)
                # elif '.' in k and k.startswith(('EQU', 'ID', 'CS', 'CT', 'I/O')) and k not in ['ID_SHORT']:
                #     _k = k.split('.')[-1]
                #     if _k not in all_interface_set:
                #         all_interface_set.add(_k)
                if '.' in k and k.startswith('ID') and k not in ['ID_SHORT']:
                    _k = k.split('.')[-1]
                    if _k not in all_interface_set:
                        all_interface_set.add(_k)
                    # 有ID_short 有ID.x 是老版本接口， ID_short后面有接口ID, 需要删除

            if len(all_interface_set) != 0:
                for _id in all_interface_set:
                    IDx = equipment.get(f'ID.{_id}')
                    _result = {
                        "building_level": building_level,
                        "field": field,
                        "system": "ES",
                        "sub_system": sub_system,
                        "interface_code": f"{sub_system};{building_level};{equipment.get('ID_SHORT') or ''};{IDx or _id or ''}",
                        "search_id": equipment.get('ID_SHORT') or '',
                        'id': f"{_id}",
                        'field_code': f'{sub_system}.{building_level}.{field}',
                        "connection_size": equipment.get(f'CS.{_id}', ''),
                        "connection_type": equipment.get(f'CT.{_id}', ''),
                        "equipment_code": equipment.get(f'EQU.{_id}', ''),
                        "cad_block_name": equipment['CAD_BLOCK_NAME'],
                        "layer": equipment['LAYER'],
                        "insert_point_x": equipment['INSERT_POINT_X'],
                        "insert_point_y": equipment['INSERT_POINT_Y'],
                        "insert_point_z": equipment['INSERT_POINT_Z'],
                        "angle": equipment['ANGLE'],
                        "true_color": equipment['TRUE_COLOR'],
                        "cad_block_id": equipment['CAD_BLOCK_ID'],
                        "distribution_box": True
                    }
                    result.append(_result)
            else:
                result = [
                    {
                        "building_level": building_level,
                        "field": field,
                        "system": "ES",
                        "sub_system": sub_system,
                        "interface_code": f"{sub_system};{building_level};{equipment.get('ID_SHORT') or ''}",
                        "search_id": equipment.get('ID_SHORT') or '',
                        'id': f"{(equipment.get('ID_SHORT', '') or '').split(';')[-1]}",
                        'field_code': f'{sub_system}.{building_level}.{field}',
                        "connection_size": equipment.get(f'CS', ''),
                        "connection_type": equipment.get(f'CT', ''),
                        "equipment_code": equipment.get(f'EQU', ''),
                        "cad_block_name": equipment['CAD_BLOCK_NAME'],
                        "layer": equipment['LAYER'],
                        "insert_point_x": equipment['INSERT_POINT_X'],
                        "insert_point_y": equipment['INSERT_POINT_Y'],
                        "insert_point_z": equipment['INSERT_POINT_Z'],
                        "angle": equipment['ANGLE'],
                        "true_color": equipment['TRUE_COLOR'],
                        "cad_block_id": equipment['CAD_BLOCK_ID'],
                        "distribution_box": True
                    }
                ]

        #BUS-F22-1-N2-11-J24;01
        return result if len(result) > 0 else final_result
    except Exception as e:
        print(f"{equipment=}")
        print(f"{filename=}")
        print(traceback.format_exc())
        # raise Exception(str(e))
        return [{
            "id": '',
            "building_level": '',
            "field": '',
            "system": '',
            "sub_system": '',
            'field_code': '',
            "interface_code": '',
            "search_id": '',
            "connection_size": '',
            "connection_type": '',
            "equipment_code": '',
            "flow_unit": '',
            "design_flow": '',
            "cad_block_name": '',
            "layer": '',
            "insert_point_x": '',
            "insert_point_y": '',
            "insert_point_z": '',
            "angle": '',
            "true_color": '',
            "cad_block_id": '',
            "distribution_box": ''
        }]

if __name__ == '__main__':
    from pathlib import Path
    eq = {'UTILIZATION_RATIO': '', 'FLOW_UNIT': '', 'DESIGN_FLOW': '', 'EQUIPMENT_CODE': '', 'INTERFACE_CODE': 'D-WwWA;WSF2;B;04', 'CS': '2"', 'CT': 'Pi', 'CAD_BLOCK_NAME': 'SEMISOFT-POC', 'LAYER': 'D-WWA', 'ANGLE': 89.99999999999999, 'TRUE_COLOR': 8, 'INSERT_POINT_X': 5480.9238, 'INSERT_POINT_Y': 14840.8932, 'INSERT_POINT_Z': 0.0, 'CENTER_POINT_X': 5480.9238, 'CENTER_POINT_Y': 14840.8932, 'CAD_BLOCK_ID': '1BEE8', 'DISTRIBUTION_BOX': False}


    result = parse_block_attributes(eq, 'YMTC^FID^PA^WS^F2.dxf')
    print(f"{result=}")
    for r in result:
        print(r['interface_code'])
