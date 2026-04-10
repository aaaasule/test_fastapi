from typing import List, Dict, Any

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_rules import BaseChangeRule
from app.fid.models import Equipment, CheckResult

import datetime
class ELDChangeValidator:
    def __init__(self, rules: List[BaseChangeRule]):
        self.rules = rules

    def validate(self, current: List[Equipment], previous: List[Equipment], request_data: Dict[str, Any]) -> List[CheckResult]:
        start_time = datetime.datetime.now()
        results = []

        for rule in self.rules:
            rule_title = f"🔍 执行规则: {rule.rule_name} ({rule.rule_type.upper()})"
            print("\n" + "=" * len(rule_title))
            print(rule_title)
            print("=" * len(rule_title))
            result = rule.check(current, previous, request_data)
            results.extend(result)

            if not result:
                print("✅ 通过 - 未发现异常")
            else:
                print(f"⚠️  发现 {len(result)} 个问题:")
                print("-" * 80)
                # 表头
                #print(f"{'#':>3} | {'类型':<12} | {'描述':<40} | {'TOOL_ID'}")
                print("-" * 80)

                for i, r in enumerate(result):
                    # 截断过长描述
                    desc = (r.description[:38] + '..') if len(r.description) > 40 else r.description
                    tool_id = r.detail.get("TOOL_ID", "N/A") or "N/A"
                    #print(f"{i + 1:>3} | {r.name:<12} | {desc:<40} | {tool_id}")

            print("")  # 空行分隔

        print(f"文件变更校验耗时 {datetime.datetime.now() - start_time}")
        return results
