import os
import re
from typing import List

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseFilenameRule
from app.fid.models import CheckResult

class FilenameFormatRule(BaseFilenameRule):
    rule_name = "文件名格式校验"
    rule_type = "error"

    def check(self, filepath, company, building, level) -> List[CheckResult]:
        filename = os.path.splitext(os.path.basename(filepath))[0]

        if filename != f"{company}^ELD^{building}^{level}":
            return [CheckResult(
                type=self.rule_type,
                name="文件名格式错误",
                description=f"格式应为 {company}^ELD^{building}^{level}",
                detail={"filename": filename}
            )]

        return []
