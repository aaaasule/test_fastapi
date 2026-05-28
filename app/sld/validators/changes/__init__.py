"""SLD 变更校验子包：可插拔规则注册池 + runner。

对外暴露：
    - run_change_checks(current, eld_sub_equipment_list) -> List[SldIssue]
        构造一次 HistoryIndex（来自 **eldSubEquipmentList**）后，遍历 CHANGE_REGISTRY 顺序执行所有
        enabled 规则。单条规则异常会被降级为一条 warning issue。
    - build_deleted_devices(current, eld_sub_equipment_list) -> List[SldDevice]
        构造 operation="delete" 的幽灵设备，供 checker 追加到 eqpData。
    - list_change_rules() -> List[Type[BaseChangeRule]]
        反射当前注册池中已启用的规则类列表。

约定：
    校验过程中，被识别为新增/属性修改/位置变更的当前设备，会就地把
    ``SldDevice.operation`` 标记为 ``"add"`` 或 ``"update"``；删除项
    不在 current 列表中，故由 ``build_deleted_devices`` 单独构造。
"""
from __future__ import annotations

from typing import Any, Dict, List, Type

from app.config import logger
from app.sld.models import SldDevice, SldIssue
from app.sld.validators.changes.base import CHANGE_REGISTRY, BaseChangeRule
from app.sld.validators.changes.common import build_history_index
from app.sld.validators.changes.deleted import build_deleted_devices

# 触发各规则模块的导入与自动注册
from app.sld.validators.changes import added  # noqa: F401
from app.sld.validators.changes import attribute_modified  # noqa: F401
from app.sld.validators.changes import deleted  # noqa: F401
from app.sld.validators.changes import position_changed  # noqa: F401


def list_change_rules() -> List[Type[BaseChangeRule]]:
    """返回当前注册池中已启用的规则类（按执行顺序）。"""
    return CHANGE_REGISTRY.all()


def run_change_checks(
    current: List[SldDevice],
    eld_sub_equipment_list: List[Dict[str, Any]],
) -> List[SldIssue]:
    """按 CHANGE_REGISTRY 顺序执行所有 change 规则；单规则异常隔离。

    所有规则共享一份预先构建的 ``HistoryIndex``，避免重复扫描历史。
    """
    history = build_history_index(eld_sub_equipment_list or [])
    issues: List[SldIssue] = []
    for rule_cls in CHANGE_REGISTRY.all():
        rule = rule_cls()
        try:
            issues.extend(rule.check(current, history))
        except Exception as exc:
            logger.exception("[SLD] change 规则执行失败 rule=%s", rule_cls.__name__)
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
    "run_change_checks",
    "list_change_rules",
    "build_deleted_devices",
    "CHANGE_REGISTRY",
    "BaseChangeRule",
]
