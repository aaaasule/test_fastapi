from typing import List

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_rules import BaseFilenameRule
from app.fid.models import CheckResult

class DXFFilenameValidator:
    def __init__(self, rules: List[BaseFilenameRule]):
        self.rules = rules

    def validate(self, filepath, **kwargs) -> List[CheckResult]:
        results = []
        for rule in self.rules:
            results.extend(rule.check(filepath, **kwargs))
        return results
