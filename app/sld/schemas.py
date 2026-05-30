# -*- coding: utf-8 -*-
"""SLD 校验 API 请求/响应模型（与《SLD和FID回填》文档一致）。"""
from __future__ import annotations

from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field


class SldIssueGroup(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    type: str
    description: str
    items: List[dict[str, Any]] = Field(default_factory=list)


class SldCheckData(BaseModel):
    """历史结构（checker 内部聚合），HTTP 对外已改为列表型 data。"""

    model_config = ConfigDict(extra="allow")

    error: List[SldIssueGroup] = Field(default_factory=list)
    warning: List[SldIssueGroup] = Field(default_factory=list)
    eqp_data: List[dict[str, Any]] = Field(default_factory=list)


class SldCheckRequest(BaseModel):
    """
    POST JSON Body，与文档「SLD校验」一致。

    - equipmentGroupList：Equipment Group 主数据；``code`` 经 buildingId 过滤后供 OWNER 编组校验。
    - eldSubEquipmentList：上一版子设备数据，变更对比（增/删/改）与回带 id/fabId 等以此为基准。
    - equipmentList：主机台清单；**新增**设备时按元素 ``code`` 与图面 ``ID_EQU`` 匹配，回带 fab/building/group 与 equipmentId。
    """

    model_config = ConfigDict(extra="ignore")

    company: dict[str, Any] = Field(default_factory=dict)
    building: dict[str, Any] = Field(default_factory=dict)
    buildingLevel: dict[str, Any] = Field(default_factory=dict)
    equipmentList: list[Any] = Field(default_factory=list)
    equipmentGroupList: list[Any] = Field(default_factory=list)
    eldSubEquipmentList: list[Any] = Field(default_factory=list)
    layerList: list[Any] = Field(default_factory=list)
    gridList: list[Any] = Field(default_factory=list)
    fab: dict[str, Any] = Field(default_factory=dict)
    file: str = ""  # local:<app/sld 下路径> 或 FTP 远端路径（无前缀）
    uploadSessionToken: str = ""  # 异步会话令牌，立即响应与回调结果均回传

