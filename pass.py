from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult
#from app.config.fid_config import FID_REQUIRED_FIELDS
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
from app.config.fid_config import FID_REQUIRED_FIELDS

from app.fid.utils.check_device import check_which_device

# VMB：接口 ID 属性键 ID.A ~ ID.Z（含 Z）
_VMB_EXPECTED_ID_KEYS = tuple(f'ID.{chr(c)}' for c in range(ord('A'), ord('Z') + 1))
# I_LINE / GPB：ID.1 ~ ID.200
_ILINE_GPB_EXPECTED_ID_KEYS = tuple(f'ID.{i}' for i in range(1, 201))
_ID_DETAIL_MAX_LIST = 80  # 描述中单类列表最多展示条数，超出则汇总条数


def _id_key_sort_key(label: str):
    """排序：数字后缀按数值，字母后缀按字典序。"""
    suf = label.split('.', 1)[-1]
    if suf.isdigit():
        return (0, int(suf))
    return (1, suf)


def _format_id_key_list(items, max_show: int = _ID_DETAIL_MAX_LIST) -> str:
    if len(items) <= max_show:
        return ', '.join(items)
    return ', '.join(items[:max_show]) + f' 等共 {len(items)} 项'


def _port_id_key_audit(eq: Dict[str, Any], device: str):
    """
    按设备类型检查期望的 ID.* 是否存在且非空。
    返回 (missing_labels, empty_labels)，无需检查则返回 None。
    """
    if str(device).startswith('VMB'):
        expected = _VMB_EXPECTED_ID_KEYS
    elif device in ('I_LINE', 'GPB'):
        expected = _ILINE_GPB_EXPECTED_ID_KEYS
    else:
        return None

    by_upper = {str(k).upper(): k for k in eq.keys()}
    missing = []
    empty = []
    for exp in expected:
        eu = exp.upper()
        if eu not in by_upper:
            missing.append(exp)
            continue
        raw_k = by_upper[eu]
        val = eq.get(raw_k)
        val = val.strip() if isinstance(val, str) else val
        if val is None or val == '':
            empty.append(exp)

    if not missing and not empty:
        return None
    missing_s = sorted(missing, key=_id_key_sort_key)
    empty_s = sorted(empty, key=_id_key_sort_key)
    return missing_s, empty_s


class FidRequiredFieldRule(BaseRule):

    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "必填项缺失"

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data = None) -> List[CheckResult]:
        results = []

        if device != None:
            equipments = equipments[device]

        for eq in equipments:
            #print(device, eq)
            missing = []
            empty = []

            attrs = eq
            device = check_which_device(eq, request_data['filename'])

            #required_fields =
            for field in FID_REQUIRED_FIELDS[device]:
                if field.upper().startswith(('CHEMICALNAME', 'GASNAME')) and request_data['fab']['name'].endswith(('1','2', '3')):
                    continue
                                                                                                                     

                #print(f"{device} {field=}")
                tmp_result = []
                field_keys = []
                for k in attrs:
                    #print(f"37{k=}")
                    if '.' in field and k.upper().startswith(field):
                        #print(f'39 {field}')
                        field_keys.append(k)
                    elif '.' not in field and k.upper() == field:
                        field_keys.append(k)
                        #print(f'43 {field}')
                #print(f"{field_keys=}")
                #continue

                for _key in field_keys:
                    #value = getattr(eq, _key.lower(), None)
                    value = eq.get(_key)
                    value = value.strip() if isinstance(value, str) else value

                    # if _key == 'GASNAME':
                    #     print(f"GASNAME {eq=}")
                    #     print(f"GASNAME {value=}")

                    if value == None:
                        missing.append(_key)
                    if value == "":
                        empty.append(_key)


                if len(field_keys) == 0:

                    #eq['detail'] =
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="关键属性缺失",
                        description=f"丢失关键业务属性：{field}",
                        detail=f"丢失关键业务属性：{field}",
                        equipment=[eq],
                        device=device
                    ))

                    print(f"{device=} 未存在必填字段{field=} {field_keys=}")
                    print(f"丢失关键业务属性field_keys eq = {eq}")

            #print(f"{missing=}")
            #print(f"{empty=}")

            if missing:
                results.append(CheckResult(
                    type=self.rule_type,
                    name="关键属性丢失",
                    description=f"丢失关键业务属性：{', '.join(missing)}",
                    detail=f"丢失关键业务属性：{', '.join(missing)}",
                    equipment=[eq],
                    device=device
                ))
                print(f"丢失关键业务属性missing eq = {eq}")

            if empty:
                results.append(CheckResult(
                    type=self.rule_type,
                    name="必填项缺失",
                    description=f"必填项未填写：{', '.join(empty)}",
                    detail=f"必填项未填写：{', '.join(empty)}",
                    equipment=[eq],
                    device=device,
                    field_or_interface='interface'
                ))
                #print(eq)

            id_audit = _port_id_key_audit(eq, device)
            if id_audit:
                missing_ids, empty_ids = id_audit
                parts = []
                if missing_ids:
                    parts.append(
                        f"缺少以下接口 ID 属性键（图中不存在）：{_format_id_key_list(missing_ids)}"
                    )
                if empty_ids:
                    parts.append(
                        f"以下接口 ID 属性键未填写值：{_format_id_key_list(empty_ids)}"
                    )
                results.append(CheckResult(
                    type=self.rule_type,
                    name="接口ID缺失明细",
                    description="；".join(parts),
                    detail="；".join(parts),
                    equipment=[eq],
                    device=device,
                    field_or_interface='interface',
                ))
        #print(f"{results=}")

        return results


if __name__ == '__main__':
    pass
