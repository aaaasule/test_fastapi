"""SLD 规范性校验：可插拔规则基类与注册池。

新增一条 spec 规则的标准流程：

    # app/sld/validators/specs/my_new_rule.py
    from app.sld.validators.specs.base import BaseSpecRule

    class MyNewRule(BaseSpecRule):
        name = "新校验"
        type = "warning"        # "error" | "warning"
        order = 60              # 数字越小越先执行
        # enabled = False       # 临时禁用

        def check(self, ctx, devices):
            ...
            return issues

随后在 ``specs/__init__.py`` 的 import 列表追加一行
``from app.sld.validators.specs import my_new_rule  # noqa: F401`` 即可
触发自动注册（Python 必须 import 到模块才会执行 ``__init_subclass__``）。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, Iterable, List, Type

from app.sld.models import SldDevice, SldFileContext, SldIssue


class _SpecRuleRegistry:
    """spec 规则注册池：按 ``(order, name)`` 升序输出已启用规则类。"""

    def __init__(self) -> None:
        self._items: List[Type["BaseSpecRule"]] = []

    def register(self, cls: Type["BaseSpecRule"]) -> None:
        if cls in self._items:
            return
        self._items.append(cls)

    def all(self) -> List[Type["BaseSpecRule"]]:
        enabled = [c for c in self._items if getattr(c, "enabled", True)]
        return sorted(enabled, key=lambda c: (c.order, c.name))

    def __iter__(self) -> Iterable[Type["BaseSpecRule"]]:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self._items)


SPEC_REGISTRY = _SpecRuleRegistry()


class BaseSpecRule(ABC):
    """规范性校验规则基类。

    类属性约定：
        name (str):     规则展示名（用于异常隔离时的占位 issue 描述）
        type (str):     ``"error"`` | ``"warning"``，仅作为元信息，
                        实际 issue 的 type 由 ``check`` 内部决定
        order (int):    执行顺序，越小越先；建议 spec 规则在 [10, 99]
        enabled (bool): 关闭某条规则时改为 False
    """

    name: ClassVar[str] = ""
    type: ClassVar[str] = "warning"
    order: ClassVar[int] = 100
    enabled: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        # 中间抽象基类（命名以下划线开头）不入池
        if cls.__name__.startswith("_"):
            return
        SPEC_REGISTRY.register(cls)

    @abstractmethod
    def check(
        self,
        ctx: SldFileContext,
        devices: List[SldDevice],
    ) -> List[SldIssue]:
        """返回本规则发现的 issue 列表（空列表表示通过）。"""
        raise NotImplementedError
