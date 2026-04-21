from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult
from app.fid.utils.parse_block_attributes import parse_block_attributes


class IdxUniqueCheck(BaseRule):
    # VMB属性块  |  i-Line/GPB等属性块

    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = 'ID.X唯一性错误'

    ID_FIELD_MAP = {
        'TAKEOFF': 'INTERFACE_CODE',
        'VMB_CHEMICAL': 'ID',
        'VMB_GASNAME': 'ID',
        'I_LINE': 'ID',
        'GPB': 'ID',
        'NEW_INTER_': 'ID',
    }

    # 设备类型 → 所需字段列表
    REQUIRED_FIELDS = {
        'TAKEOFF': ['sub_system', 'building_level', 'field', 'id'],
        'VMB_CHEMICAL': ['sub_system', 'building_level', 'field'],
        'VMB_GASNAME': ['sub_system', 'building_level', 'field'],
        'I_LINE': ['sub_system', 'building_level'],
        'GPB': ['sub_system', 'building_level'],
        'NEW_INTER_': ['sub_system', 'building_level'],
    }

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data=None) -> List[
        CheckResult]:
        """
        对所有 equipment 执行 INTERFACE_CODE 校验。

        Args:
            equipments: 二维列表，通常外层是区域/系统，内层是设备
            device: 设备类型，如 'TAKEOFF', 'VMB' 等

        Returns:
            List[CheckResult]
        """

        if device != None:
            equipments = equipments[device]

        if len(equipments) == 0:
            return []

        results = []

        for eq in equipments:
            equipments_infos = parse_block_attributes(eq, request_data['filename'])

            idx_cache = []
            idx_seen = {}
            # print(f"{eq=}")
            for key in eq:
                # print(f"{key=} {eq[key]=}")
                if key.startswith('ID.') and eq[key]:
                    if eq[key] not in idx_seen:
                        # idx_seen.add(eq[key])
                        idx_seen[eq[key]] = [key]
                    else:
                        # print(f"{eq[key]=}")
                        idx_seen[eq[key]].append(key)
                        # print(f"{idx_seen=}")

            description = '同一属性块中:'
            dup_info = []
            for k, v in idx_seen.items():
                # print(f"{k=} {v=} {type(v)} {len(v)}")
                if len(v) > 1:
                    description += f"{','.join(v)}重复"
                    # logger.info(f"{description=}")
                    dup_suffixes = {key.split('.', 1)[-1] for key in v}
                    # logger.info(f"dup_suffixes:{dup_suffixes}")
                    dup_info.extend(
                        info for info in equipments_infos if info.get('x') in dup_suffixes
                    )
            from app.config import logger
            # logger.info(f"dup_info:{dup_info}")
            if len(description) > 7:
                # logger.info(f"dup_info——IDx:{dup_info}")
                logger.info(f"dup_info——device:{device}")
                if len(dup_info) > 0:
                    idx = ''
                    if device in ['I_LINE', 'GPB']:
                        idx = ';' + dup_info[0].get('IDx')
                    elif device.startswith('VMB'):
                        idx = '-' + dup_info[0].get('IDx')

                    eq['idx'] = idx
                # logger.info(f"dup_info——IDx--eq:{eq}")
                results.append(CheckResult(
                    type=self.rule_type,
                    name="ID.X唯一性错误",
                    description=description,
                    detail=description,
                    equipment=[eq],
                    device=device
                ))

        return results


if __name__ == '__main__':
    import sys
    from pathlib import Path

    print(sys.path)
    print(Path('./').absolute().parent.parent)
    sys.path.append(str(Path('./').absolute().parent.parent.parent))
    from eld_validator.fid_parse import parse_dxf

    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PA^FAB1^F2.dxf'  # take off
    # dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PC^FAB2^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB1^F2.dxf'
    dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.PS^FAB2^F2.dxf'
    # dxf_path = r'D:\pycharm\eld_validator\data\fid\YMTC^FID.ES^FAB2^F2.dxf'

    eqps = parse_dxf(dxf_path)

    request_data = {'field&interface': {'N208V-3P;FAB2F2-BUS-F21-1-N2-15-Q10':
                                            {'sub_system': 'U-3P;FAB2F2-F22-1-2I-LINE-U2-05-63D2716'}}
                    }
    for eq in eqps:
        if not eq.startswith('VMB_GASNAME'):
            continue

        rule = InterfaceCodeRule()
        results = rule.check(eqps, device=eq, request_data=request_data)

        for r in results:
            print(r)
