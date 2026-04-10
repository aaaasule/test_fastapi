from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import Equipment, CheckResult

def _is_valid_code(code: Any) -> bool:
    """判断 code 是否有效（非 None 且不是 'null' 字符串）"""
    if code is None:
        return False
    code_str = str(code).strip()
    return code_str.lower() != 'null'

class ValidateEquipmentOwner(BaseRule):
    rule_type = "error"

    def check(self, equipments: List[Equipment], check_info: Any, request_data: Dict[str, Any]) -> List[CheckResult]:
        results = []

        # 提取有效的、大写的 owner code 集合（用于快速查找）
        equipments_limit = check_info.get('equipment_group_list', [])
        valid_owners = {
            str(item['code']).upper()
            for item in equipments_limit
            if _is_valid_code(item['code'])
        }

        for eq in equipments:
            owner_upper = None
            if eq.owner is not None:
                owner_upper = str(eq.owner).upper()

                print(f"{eq.tool_id=} {eq.group_id=}")
                # 如果 owner 为空，或不在允许列表中，则报错
                #if owner_upper not in valid_owners or eq.group_id is None:
                if owner_upper not in valid_owners:
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="设备编组错误",
                        description=f"OWNER字段({owner_upper})不在允许的equipment group内",
                        detail={
                            "TOOL_ID": eq.tool_id,
                            "OWNER": eq.owner,
                            "坐标X": eq.insert_point_x,
                            "坐标Y": eq.insert_point_y
                        },
                        equipment=eq
                    ))
                    # 安全打印
                    print(f"{owner_upper=} {eq.tool_id=}")

        return results
