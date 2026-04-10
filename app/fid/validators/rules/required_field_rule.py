from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import Equipment, CheckResult
#from app.config.fid_config import REQUIRED_FIELDS
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
from app.config.fid_config import REQUIRED_FIELDS

class RequiredFieldRule(BaseRule):
    rule_name = 'RequiredFieldRule'
    rule_type = "error"

    def check(self, equipments: List[Equipment], check_info: Any, request_data: Dict[str, Any]) -> List[CheckResult]:
        # === 规则标题 ===
        # rule_title = f"🔍 执行规则: {self.rule_name} ({self.rule_type.upper()})"
        # print("\n" + "=" * len(rule_title))
        # print(rule_title)
        # print("=" * len(rule_title))

        results = []
        for eq in equipments:
            missing = []
            empty = []
            for field in REQUIRED_FIELDS:
                value = getattr(eq, field.lower(), '')
                if value is None:
                    missing.append(field.upper())
                elif isinstance(value, str) and value.strip() == "":
                    empty.append(field.upper())

            if missing:
                results.append(CheckResult(
                    type=self.rule_type,
                    name="关键属性丢失",
                    description=f"缺少关键业务属性：{', '.join(missing)}",
                    detail={
                        "TOOL_ID": eq.tool_id,
                        "缺少属性字段": ", ".join(missing),
                        "坐标X": eq.insert_point_x,
                        "坐标Y": eq.insert_point_y
                    },
                    equipment=eq
                ))
            if empty:
                results.append(CheckResult(
                    type=self.rule_type,
                    name="必填项缺失",
                    description=f"必填项未填写：{', '.join(empty)}",
                    detail={
                        "TOOL_ID": eq.tool_id,
                        "未填写字段": ", ".join(empty),
                        "坐标X": eq.insert_point_x,
                        "坐标Y": eq.insert_point_y
                    },
                    equipment=eq
                ))


        return results
