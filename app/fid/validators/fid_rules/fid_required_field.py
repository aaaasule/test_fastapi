from typing import List, Any, Dict
import re

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


def _fab_is_fab1_or_fab2(request_data: Dict[str, Any] | None) -> bool:
    """
    是否 FAB1 / FAB2 厂区（用于关闭部分 VMB 的 ID.x 空值校验）。

    约定：fab.id 为厂区编号（与名称中 Fab 后的数字一致，如 id=3 对应 Fab3）；
    fab.name 为厂区名称。优先用 id；无法解析时再从 name 末尾连续数字推断。
    """
    fab = (request_data or {}).get('fab') or {}
    n = None
    raw_id = fab.get('id')
    if raw_id is not None and str(raw_id).strip() != '':
        try:
            n = int(raw_id)
        except (TypeError, ValueError):
            n = None
    if n is None:
        name = fab.get('name')
        if name is not None:
            m = re.search(r'(\d+)\s*$', str(name).strip())
            if m:
                try:
                    n = int(m.group(1))
                except ValueError:
                    n = None
    return n in (1, 2)


def _skip_cs_validation(request_data: Dict[str, Any] | None) -> bool:
    system = (request_data or {}).get('system') or {}
    system_code = str(system.get('code') or '').strip().upper()
    return _fab_is_fab1_or_fab2(request_data) and system_code == 'ES'


def _should_validate_pc_io_change(request_data: Dict[str, Any] | None) -> bool:
    """PC 系统校验图块 I/O 与接口 in_out_code 是否一致；FAB1 / FAB2 厂区跳过。"""
    if _fab_is_fab1_or_fab2(request_data):
        return False
    system = (request_data or {}).get('system') or {}
    return str(system.get('code') or '').strip().upper() == 'PC'


def _port_suffixes_from_equ_ct_cs(eq: Dict[str, Any], include_cs: bool = True) -> set:
    """从 EQU.{suffix}、CT.{suffix}、CS.{suffix} 收集端口后缀（suffix 不含点）。"""
    out = set()
    for k in eq:
        if '.' not in k:
            continue
        ku = str(k).upper()
        head, tail = ku.split('.', 1)
        if head not in _CT_CS_EQU_PREFIXES or not tail or '.' in tail:
            continue
        if head == 'CS' and not include_cs:
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


def _id_required_by_port_keys_audit(eq: Dict[str, Any], device: str, request_data: Dict[str, Any] | None = None):
    """
    VMB：若存在 EQU.x、CT.x、CS.x，则必须有 ID.x。

    FAB1 / FAB2 的 ES 系统不校验。

    返回 (missing_labels, empty_labels)，无需检查则返回 None。
    """
    if not str(device).startswith('VMB'):
        return None
    if _skip_cs_validation(request_data):
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


def _is_cs_required_field(field: str) -> bool:
    field_u = str(field).upper()
    return field_u == 'CS' or field_u.startswith('CS.')


def _skip_io_presence_validation(device: str, field: str) -> bool:
    """VMB_CHEMICAL：I/O 不校验 tag 是否存在，仅 tag 存在但为空时报「必填项未填写」。"""
    return device == 'VMB_CHEMICAL' and str(field).upper().startswith('I/O')


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

            # 配置项「整类缺失」（无任何匹配键）合并为一条，避免 api_util 按 errorName 去重后只保留 CT. 等一条
            critical_patterns_missing = []

            #required_fields =
            for field in FID_REQUIRED_FIELDS[device]:
                if _is_cs_required_field(field) and _skip_cs_validation(request_data):
                    continue
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

                    if _skip_io_presence_validation(device, field):
                        if value is None or value == "":
                            empty.append(_key)
                    else:
                        if value == None:
                            missing.append(_key)
                        if value == "":
                            empty.append(_key)


                if len(field_keys) == 0 and not _skip_io_presence_validation(device, field):
                    critical_patterns_missing.append(field)

            if critical_patterns_missing:
                joined = "，".join(critical_patterns_missing)
                results.append(CheckResult(
                    type=self.rule_type,
                    name="关键属性缺失",
                    description=f"图块问题,丢失关键业务属性：{joined}",
                    detail=f"图块问题,丢失关键业务属性：{joined}",
                    equipment=[eq],
                    device=device
                ))
                print(f"{device=} 未存在必填字段(合并)：{critical_patterns_missing=} eq={eq}")

            #print(f"{missing=}")
            #print(f"{empty=}")

            if missing:
                results.append(CheckResult(
                    type=self.rule_type,
                    name="关键属性丢失",
                    description=f"图块问题,丢失关键业务属性：{', '.join(missing)}",
                    detail=f"图块问题,丢失关键业务属性：{', '.join(missing)}",
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

            id_audit = _id_required_by_port_keys_audit(eq, device, request_data)
            if id_audit:
                miss_ids, empty_ids = id_audit
                parts = []
                if miss_ids:
                    parts.append(
                        f"图块问题,缺少 {_format_id_label_list(miss_ids)} 属性字段"
                    )
                if empty_ids:
                    parts.append(
                        f"必填项未填写：{_format_id_label_list(empty_ids)}"
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
