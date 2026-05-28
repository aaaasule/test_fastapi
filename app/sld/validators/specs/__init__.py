"""SLD 规范性校验子包：可插拔规则注册池 + runner。

对外暴露：
    - run_spec_checks(ctx, devices) -> List[SldIssue]
        遍历 SPEC_REGISTRY 按 (order, name) 升序执行所有 enabled 规则。
        单条规则异常会被降级为一条 warning issue，不阻断其它规则。
    - list_spec_rules() -> List[Type[BaseSpecRule]]
        反射当前注册池中已启用的规则类列表。
    - business_key(d): 业务键工具，供变更校验等共用。
"""
from __future__ import annotations

from typing import List, Type

from app.config import logger
from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.validators.specs.base import SPEC_REGISTRY, BaseSpecRule
from app.sld.validators.specs.common import (
    ERROR_KEY_ATTRS,
    KEY_ATTR_KEYS,
    KEY_ATTRS,
    WARNING_KEY_ATTRS,
    base_detail,
    business_key,
)

# 触发各规则模块的导入与自动注册（顺序无关，runner 会按 order 排序）
from app.sld.validators.specs import efms_id_equ  # noqa: F401
from app.sld.validators.specs import filename  # noqa: F401
from app.sld.validators.specs import id_equ_format  # noqa: F401
from app.sld.validators.specs import owner_group  # noqa: F401
from app.sld.validators.specs import required  # noqa: F401
from app.sld.validators.specs import uniqueness  # noqa: F401


def list_spec_rules() -> List[Type[BaseSpecRule]]:
    """返回当前注册池中已启用的规则类（按执行顺序）。"""
    return SPEC_REGISTRY.all()


def run_spec_checks(
    ctx: SldFileContext,
    devices: List[SldDevice],
) -> List[SldIssue]:
    """按 SPEC_REGISTRY 顺序执行所有 spec 规则；单规则异常隔离。"""
    issues: List[SldIssue] = []
    for rule_cls in SPEC_REGISTRY.all():
        rule = rule_cls()
        try:
            issues.extend(rule.check(ctx, devices))
        except Exception as exc:  # 单条规则异常不阻断其它规则
            logger.exception("[SLD] spec 规则执行失败 rule=%s", rule_cls.__name__)
            issues.append(
                SldIssue(
                    type="warning",
                    name=f"规则执行失败:{rule.name or rule_cls.__name__}",
                    description=f"规则 {rule_cls.__name__} 执行异常",
                    detail={"rule": rule_cls.__name__, "exception": str(exc)},
                )
            )
    return issues


__all__ = [
    "run_spec_checks",
    "list_spec_rules",
    "business_key",
    "base_detail",
    "KEY_ATTRS",
    "ERROR_KEY_ATTRS",
    "WARNING_KEY_ATTRS",
    "KEY_ATTR_KEYS",
    "SPEC_REGISTRY",
    "BaseSpecRule",
]
