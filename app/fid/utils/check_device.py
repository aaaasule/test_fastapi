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
                elif 'BUS' in equipment.get('ID_SHORT').upper():
                    return 'NEW_INTER_'
                else:
                    return 'I_LINE'

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
        elif 'BUS' in equipment.get('ID_SHORT').upper():
            return 'NEW_INTER_'

    return 'I_LINE'
    '''
ES系统只校验有ID_short的块， 有GPB、ILINE可以确定块类， 如果没有根据 ID是否BUS开头判断是否是新旧接口。
- 如果有BUS 并且有ID.X是旧接口，只有ID是新接口
- 如果判断不出来那么认为是 [其他块], 用ILINE规则校验， 可以根据ID的前缀判断是什么块。ID前缀跟新接口相同有分类标识。

- 旧接口不校验CS
    '''

    print(f"未识别device - {equipment=}")


