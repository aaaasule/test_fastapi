from typing import List, Any, Dict

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from .base_rules import BaseRule, FIDBaseRule
from app.fid.models import Equipment, CheckResult

import datetime

class ELDRuleValidator:
    def __init__(self, rules: List[BaseRule]):
        self.rules = rules

    def validate(self, equipments: List[Equipment], check_info: Any, request_data: Dict[str, Any]) -> List[CheckResult]:


        start_time = datetime.datetime.now()
        results = []

        for rule in self.rules:
            rule_title = f"🔍 执行规则: {rule.rule_name} ({rule.rule_type.upper()})"
            print("\n" + "=" * len(rule_title))
            print(rule_title)
            print("=" * len(rule_title))

            result = rule.check(equipments, check_info, request_data)
            results.extend(result)

            # === 输出结果 ===
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

        print(f"规范校验耗时 {datetime.datetime.now() - start_time}")
        return results



class FIDRuleValidator:
    def __init__(self, rules: Dict[str, List[FIDBaseRule]]):
        self.rules = rules

    def validate(self, equipments: Dict[str, List[Equipment]], request_data: Any) -> List[CheckResult]:


        start_time = datetime.datetime.now()
        results = []
        for device in self.rules:
            rules = self.rules[device]

            if len(equipments[device]) == 0:
                continue

            for rule in rules:
                rule_title = f"🔍 执行规则: {rule.rule_name} ({rule.rule_type.upper()})"
                print("\n" + "=" * len(rule_title))
                print(device,  rule_title)
                print("=" * len(rule_title))

                # if '删除' in rule.rule_name:
                #     total_equipments = []
                #     for device in equipments:
                #         total_equipments.extend(equipments[device])
                #
                #     result = rule.check(total_equipments, device, request_data)
                # else:
                #     result = rule.check(equipments, device, request_data)

                result = rule.check(equipments, device, request_data)
                results.extend(result)

                # === 输出结果 ===
                if not result:
                    print("✅ 通过 - 未发现异常")
                else:
                    print(f"⚠️  发现 {len(result)} 个问题:")
                    print("-" * 80)
                    # for r in result:
                    #     print(r)
                    # 表头
                    #print(f"{'#':>3} | {'类型':<12} | {'描述':<40} | {'TOOL_ID'}")
                    print("-" * 80)

                    for i, r in enumerate(result):
                        # 截断过长描述
                        desc = (r.description[:38] + '..') if len(r.description) > 40 else r.description
                        tool_id = (
                                r.equipment[0].get("INTERFACE_ID") or
                                r.equipment[0].get("ID_SHORT") or
                                r.equipment[0].get("ID") or
                                "N/A"
                        )
                        #print(f"{i + 1:>3} | {r.name:<12} | {desc:<40} | {tool_id}")

                print("")  # 空行分隔

                print(f"{device}已有{len(results)}个结果，规范校验耗时 {datetime.datetime.now() - start_time}")
        return results


class FIDDeleteValidator:
    def __init__(self, rules: Dict[str, List[FIDBaseRule]]):
        self.rules = rules

    def validate(self, equipments: Dict[str, List[Equipment]], request_data: Any) -> List[CheckResult]:


        start_time = datetime.datetime.now()
        results = []

        total_equipments = []
        for device in equipments:
            total_equipments.extend(equipments[device])


        for rule in self.rules:
            rule_title = f"🔍 执行规则: {rule.rule_name} ({rule.rule_type.upper()})"
            print("\n" + "=" * len(rule_title))
            print(rule_title)
            print("=" * len(rule_title))

            result = rule.check(total_equipments, device, request_data)
            results.extend(result)

            # === 输出结果 ===
            if not result:
                print("✅ 通过 - 未发现异常")
            else:
                print(f"⚠️  发现 {len(result)} 个问题:")
                print("-" * 80)
                # for r in result:
                #     print(r)
                # 表头
                #print(f"{'#':>3} | {'类型':<12} | {'描述':<40} | {'TOOL_ID'}")
                print("-" * 80)
            print("")  # 空行分隔

            print(f"{device}已有{len(results)}个结果，规范校验耗时 {datetime.datetime.now() - start_time}")
        return results
