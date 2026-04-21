from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult

# from app.config.fid_config import FID_REQUIRED_FIELDS
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
from app.fid.utils.parse_block_attributes import parse_block_attributes


class FidRequiredFieldRule(BaseRule):
    eqp_type = 'TAKEOFF'
    rule_type = "error"
    rule_name = "必填项缺失"

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data=None) -> List[
        CheckResult]:
        results = []

        if device != None:
            equipments = equipments[device]

        for eq in equipments:
            # print(device, eq)
            missing = []
            empty = []

            attrs = eq
            device = check_which_device(eq, request_data['filename'])

            # required_fields =
            for field in FID_REQUIRED_FIELDS[device]:
                if field.upper().startswith(('CHEMICALNAME', 'GASNAME')) and request_data['fab']['name'].endswith(
                        ('1', '2', '3')):
                    continue
                if field.upper().startswith('CS') and request_data['fab']['name'].endswith(('1', '2')) and 'ES' in \
                        request_data['filename']:
                    continue

                # print(f"{device} {field=}")
                tmp_result = []
                field_keys = []
                for k in attrs:
                    # print(f"37{k=}")
                    if '.' in field and k.upper().startswith(field):
                        # print(f'39 {field}')
                        field_keys.append(k)
                    elif '.' not in field and k.upper() == field:
                        field_keys.append(k)
                        # print(f'43 {field}')
                # print(f"{field_keys=}")
                # continue

                for _key in field_keys:
                    # value = getattr(eq, _key.lower(), None)
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
                    # eq['detail'] =
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

            # print(f"{missing=}")
            # print(f"{empty=}")

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
                    device=device
                ))


            # equipments_infos = parse_block_attributes(eq, request_data['filename'])
            # for equipments_info in equipments_infos:
            #     for e in empty:
            #         if e.upper().startswith('ID.') or e.upper().startswith('CS.') or e.upper().startswith('CT.'):
            #             results.append(CheckResult(
            #                 type=self.rule_type,
            #                 name="必填项缺失",
            #                 description=f"必填项未填写：{', '.join(empty)}",
            #                 detail=f"必填项未填写：{', '.join(empty)}",
            #                 equipment=[eq, equipments_info],
            #                 device=device
            #             ))
            #         else:
            #             results.append(CheckResult(
            #                 type=self.rule_type,
            #                 name="必填项缺失",
            #                 description=f"必填项未填写：{', '.join(empty)}",
            #                 detail=f"必填项未填写：{', '.join(empty)}",
            #                 equipment=[eq, equipments_info],
            #                 device=device
            #             ))
                # print(eq)
        # print(f"{results=}")

        return results


if __name__ == '__main__':
    pass
