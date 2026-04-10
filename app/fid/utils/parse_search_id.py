import json

#from app.fid.utils.check_device import check_which_device

import traceback
from typing import List, Any, Dict
import re


def check_which_device(equipment: Dict[str, Any], filename: Any):
    for _tail in ['PA', 'PD', 'PE', 'PV', 'PP', 'PW']:
        if f'FID.{_tail}' in filename:
            return 'TAKEOFF'

    for _tail in ['PC']:
        if f'FID.{_tail}' in filename:
            return 'VMB_CHEMICAL'  # PC只有chemical  PS只有gasname
    for _tail in ['PS']:
        if f'FID.{_tail}' in filename:
            return 'VMB_GASNAME'

    for _tail in ['PB']:
        if f'FID.{_tail}' in filename:
            if 'INTERFACE_CODE' in equipment:
                return 'TAKEOFF'
            else:
                return 'VMB_GASNAME'  # PB只有gasname

    for _tail in ['ES']:
        if f'FID.{_tail}' in filename:
            if equipment.get('ID_SHORT'):
                # print(f"ID_SHORT-{equipment.get('ID_SHORT')}")
                if 'GPB' in equipment.get('ID_SHORT').upper():
                    return 'GPB'
                elif 'LINE' in equipment.get('ID_SHORT').upper():
                    return 'I_LINE'
                else:
                    return 'NEW_INTER_'

    if 'INTERFACE_CODE' in equipment:
        return 'TAKEOFF'
    elif 'VMB-TYPE' in equipment:
        if 'CHEMICALNAME' in equipment:
            return 'VMB_CHEMICAL'
        elif 'GASNAME' in equipment:
            return 'VMB_GASNAME'

    elif equipment.get('ID_SHORT'):
        if 'GPB' in equipment.get('ID_SHORT', '').upper():
            return 'GPB'
        elif 'LINE' in equipment.get('ID_SHORT', '').upper():
            return 'I_LINE'
        elif equipment.get('ID', '').upper().startswith('BUS'):
            return 'NEW_INTER_'

    return 'I_LINE'


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


def parse_search_id(result, system):
    try:

        #print(f"[parse_search_id] {result}")


        system = system.get('name', '')

        device = check_which_device(result.equipment[-1], f"FID.{system}")
        #print(f"[parse_search_id] {device=}")

        #print("")
        if device == 'TAKEOFF':
            return str(result.equipment[-1].get('UNI_CODE') or '')

        elif device.startswith('VMB'):
            return str(result.equipment[0]['UNI_CODE'] or '')

        elif device in ['I_LINE', 'GPB']:
            return str(result.equipment[0].get('CODE') or '')

        elif device == 'NEW_INTER_':  # 新接口
            return str(result.equipment[0].get('CODE') or '')
        else:
            return ''
    except Exception as e:
        print(traceback.format_exc())
        # raise Exception(str(e))
        return ''

if __name__ == '__main__':
    pass
