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

# 由端口键推导必须存在的 ID.{suffix}：仅 EQU.x / CT.x / CS.x（与业务约定一致）
_CT_CS_EQU_PREFIXES = ('CT', 'CS', 'EQU')
_ID_DETAIL_MAX_LIST = 80


def _port_suffixes_from_equ_ct_cs(eq: Dict[str, Any]) -> set:
    """从 EQU.{suffix}、CT.{suffix}、CS.{suffix} 收集端口后缀（suffix 不含点）。"""
    out = set()
    for k in eq:
        if '.' not in k:
            continue
        ku = str(k).upper()
        head, tail = ku.split('.', 1)
        if head not in _CT_CS_EQU_PREFIXES or not tail or '.' in tail:
            continue
        out.add(tail)
    return out


def _suffix_sort_key(s: str):
    if s.isdigit():
        return (0, int(s), len(s), s)
    return (1, s)


def _format_id_label_list(labels, max_show: int = _ID_DETAIL_MAX_LIST) -> str:
    if len(labels) <= max_show:
        return ', '.join(labels)
    return ', '.join(labels[:max_show]) + f' 等共 {len(labels)} 项'


def _id_required_by_port_keys_audit(eq: Dict[str, Any], device: str):
    """
    VMB / I_LINE / GPB：若存在 EQU.x、CT.x、CS.x，则必须有 ID.x 且非空。
    返回 (missing_labels, empty_labels)，无需检查则返回 None。
    """
    if not (str(device).startswith('VMB') or device in ('I_LINE', 'GPB')):
        return None

    suffixes = _port_suffixes_from_equ_ct_cs(eq)
    if not suffixes:
        return None

    by_upper = {str(k).upper(): k for k in eq.keys()}
    missing = []
    empty = []
    for suf in sorted(suffixes, key=_suffix_sort_key):
        id_label = f'ID.{suf}'
        id_u = id_label.upper()
        if id_u not in by_upper:
            missing.append(id_label)
            continue
        raw_k = by_upper[id_u]
        val = eq.get(raw_k)
        val = val.strip() if isinstance(val, str) else val
        if val is None or val == '':
            empty.append(id_label)

    if not missing and not empty:
        return None
    return missing, empty


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

            id_audit = _id_required_by_port_keys_audit(eq, device)
            if id_audit:
                miss_ids, empty_ids = id_audit
                parts = []
                if miss_ids:
                    parts.append(
                        f"端口已定义（EQU/CT/CS）但缺少对应接口 ID 键：{_format_id_label_list(miss_ids)}"
                    )
                if empty_ids:
                    parts.append(
                        f"以下接口 ID 键未填写值：{_format_id_label_list(empty_ids)}"
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
