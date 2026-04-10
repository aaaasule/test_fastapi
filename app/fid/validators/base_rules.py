from abc import ABC, abstractmethod
from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent

sys.path.insert(0, str(project_root))

from app.fid.models import Equipment, CheckResult
from app.fid.schemas import CheckerInfo


# 原子规则基类
class BaseRule(ABC):
    rule_name: str = ""
    rule_type: str = ""  # "error" or "warning"

    @abstractmethod
    def check(self, equipments: List[Equipment], check_info: CheckerInfo, request_data: Dict[str, Any]) -> List[
        CheckResult]:
        pass


class FIDBaseRule(ABC):
    rule_name: str = ""
    rule_type: str = ""  # "error" or "warning"

    @abstractmethod
    def check(self, equipments, device, request_data) -> List[CheckResult]:
        pass


# 文件名校验原子规则基类（只校验文件名）
class BaseFilenameRule(ABC):
    rule_name: str
    rule_type: str

    @abstractmethod
    def check(self, filepath, company, building, level) -> List[CheckResult]:
        pass


# 变更校验原子规则基类
class BaseChangeRule(ABC):
    rule_name: str
    rule_type: str

    @abstractmethod
    def check(self, current: List[Equipment], previous: List[Equipment], request_data: Dict[str, Any]) -> List[
        CheckResult]:
        pass


# 变更校验原子规则基类
class BaseSearchRule(ABC):
    rule_name: str
    rule_type: str

    @abstractmethod
    def check(self, current: List[Equipment], previous: List[Equipment]) -> List[CheckResult]:
        pass
