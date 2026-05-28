"""SLD 变更校验：可插拔规则基类与注册池。

新增一条 change 规则的标准流程：

    # app/sld/validators/changes/my_new_rule.py
    from app.sld.validators.changes.base import BaseChangeRule

    class MyNewRule(BaseChangeRule):
        name = "新变更校验"
        type = "warning"
        order = 150

        def check(self, current, history):
            ...
            return issues

随后在 ``changes/__init__.py`` 的 import 列表追加一行
``from app.sld.validators.changes import my_new_rule  # noqa: F401`` 即可
触发自动注册。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Iterable, List, Type

from app.sld.models import SldDevice, SldIssue
from app.sld.validators.changes.common import HistoryIndex


class _ChangeRuleRegistry:
    """change 规则注册池：按 ``(order, name)`` 升序输出已启用规则类。"""

    def __init__(self) -> None:
        self._items: List[Type["BaseChangeRule"]] = []

    def register(self, cls: Type["BaseChangeRule"]) -> None:
        if cls in self._items:
            return
        self._items.append(cls)

    def all(self) -> List[Type["BaseChangeRule"]]:
        enabled = [c for c in self._items if getattr(c, "enabled", True)]
        return sorted(enabled, key=lambda c: (c.order, c.name))

    def __iter__(self) -> Iterable[Type["BaseChangeRule"]]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self._items)


CHANGE_REGISTRY = _ChangeRuleRegistry()


class BaseChangeRule(ABC):
    """变更校验规则基类。

    所有变更规则共享一份预先构建好的 ``HistoryIndex``，避免重复扫描历史。
    单条规则除返回 ``List[SldIssue]`` 外，可就地把 ``device.operation``
    标记为 ``"add" / "update"``。删除项不在 ``current`` 中，由
    ``build_deleted_devices`` 单独构造。
    """

    name: ClassVar[str] = ""
    type: ClassVar[str] = "warning"
    order: ClassVar[int] = 100
    enabled: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name__.startswith("_"):
            return
        CHANGE_REGISTRY.register(cls)

    @abstractmethod
    def check(
        self,
        current: List[SldDevice],
        history: HistoryIndex,
    ) -> List[SldIssue]:
        """返回本规则发现的 issue 列表（空列表表示通过）。"""
        raise NotImplementedError
