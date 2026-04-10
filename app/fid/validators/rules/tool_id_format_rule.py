import re
from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import Equipment, CheckResult
#from app.config.fid_config import TOOL_ID_PATTERN
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
from app.config.fid_config import TOOL_ID_PATTERN

class ToolIdFormatRule(BaseRule):
    rule_name = "TOOL_ID格式校验"
    rule_type = "error"

    def check(self, equipments: List[Equipment], check_info: Any, request_data: Dict[str, Any]) -> List[CheckResult]:
        # rule_title = f"🔍 执行规则: {self.rule_name} ({self.rule_type.upper()})"
        # print("\n" + "=" * len(rule_title))
        # print(rule_title)
        # print("=" * len(rule_title))

        results = []
        for eq in equipments:
            if not re.match(TOOL_ID_PATTERN, eq.tool_id):
                results.append(CheckResult(
                    type=self.rule_type,
                    name="TOOL_ID规范错误",
                    description="设备命名应以大写字母开头，（只允许'-'）",
                    detail={
                        "CAD编码": eq.cad_block_id,
                        "TOOL_ID": eq.tool_id,
                        "坐标X": eq.insert_point_x,
                        "坐标Y": eq.insert_point_y
                    },
                    equipment=eq
                ))


        return results
