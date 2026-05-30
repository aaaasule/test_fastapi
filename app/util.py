# -*- coding: utf-8 -*-
"""跨模块通用工具：异步校验立即响应与结果回调。"""
from __future__ import annotations

import asyncio
import traceback
from collections.abc import Callable
from functools import partial
from typing import Any

import requests

from app.config import logger
from app.config.fid_config import SYNC_BASE_URL

_FID_ROW_KEYS = ("interfaces", "field")
_FID_META_KEYS = frozenset(
    {
        "interfaces_add",
        "interfaces_update",
        "interfaces_delete",
        "fields_add",
        "fields_update",
        "fields_delete",
        "interfaces_num",
        "field_nums",
    }
)


def build_sync_callback_url(callback_path: str) -> str:
    """拼接 ``sync_base_url`` 与回调相对路径。"""
    base = (SYNC_BASE_URL or "").rstrip("/")
    path = (callback_path or "").strip().strip('"').strip("'").lstrip("/")
    if not base or not path:
        return ""
    return f"{base}/{path}"


def make_async_accept_response(
    upload_session_token: str,
    *,
    x_fab_ds: str = "",
) -> dict[str, Any]:
    payload = {
        "code": 200,
        "message": "请求已接收，校验处理中",
        "success": True,
        "uploadSessionToken": upload_session_token,
    }
    if x_fab_ds:
        payload["X-Fab-Ds"] = x_fab_ds
    return payload


def make_task_error_response(message: str, *, detail: str | None = None) -> dict[str, Any]:
    return {
        "code": 400,
        "message": message,
        "success": False,
        "data": [{"errors": [detail or message]}],
    }


def _item_has_errors(item: dict[str, Any]) -> bool:
    errs = item.get("errors")
    if isinstance(errs, list):
        return len(errs) > 0
    return bool(errs)


def _split_list_rows(data: list[Any]) -> tuple[list[Any], list[Any]]:
    errors: list[Any] = []
    successes: list[Any] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if _item_has_errors(item):
            errors.append(item)
        else:
            successes.append(item)
    return errors, successes


def _split_fid_rows(data: dict[str, Any]) -> tuple[list[Any], list[Any]]:
    errors: list[Any] = []
    successes: list[Any] = []
    for key in _FID_ROW_KEYS:
        for item in data.get(key) or []:
            if not isinstance(item, dict):
                continue
            if _item_has_errors(item):
                errors.append(item)
            else:
                successes.append(item)
    return errors, successes


def _system_error_rows(result: dict[str, Any]) -> list[Any]:
    data = result.get("data")
    message = str(result.get("message") or "算法调用失败")
    if isinstance(data, list) and data:
        return list(data)
    return [{"errors": [message]}]


def _attach_callback_context(
    payload: dict[str, Any],
    upload_session_token: str,
    *,
    x_fab_ds: str = "",
) -> dict[str, Any]:
    out = dict(payload)
    out["uploadSessionToken"] = upload_session_token
    if x_fab_ds:
        out["X-Fab-Ds"] = x_fab_ds
    return out


def format_parse_callback_payload(
    result: dict[str, Any],
    upload_session_token: str,
    *,
    module: str = "SLD",
    x_fab_ds: str = "",
) -> dict[str, Any]:
    """
    将各模块内部校验结果转为统一回调结构::

        {
            "uploadSessionToken": "...",
            "success": true/false,
            "errorMessage": "...",
            "errors": [...],
            "successes": [...],
        }
    """
    code = int(result.get("code") or 200)
    message = str(result.get("message") or "").strip()
    data = result.get("data")
    old_success = result.get("success")

    if code == 400 or (old_success is None and result.get("traceback")):
        return _attach_callback_context(
            {
                "success": False,
                "errorMessage": message or "算法调用失败",
                "errors": _system_error_rows(result),
                "successes": [],
            },
            upload_session_token,
            x_fab_ds=x_fab_ds,
        )

    module_upper = (module or "SLD").upper()
    if module_upper == "FID" and isinstance(data, dict):
        errors, successes = _split_fid_rows(data)
    elif isinstance(data, list):
        errors, successes = _split_list_rows(data)
    else:
        errors, successes = [], []

    if old_success is False or errors:
        return _attach_callback_context(
            {
                "success": False,
                "errorMessage": message or "校验失败",
                "errors": errors if errors else (list(data) if isinstance(data, list) else []),
                "successes": successes,
            },
            upload_session_token,
            x_fab_ds=x_fab_ds,
        )

    return _attach_callback_context(
        {
            "success": True,
            "errorMessage": message or "调用成功",
            "errors": [],
            "successes": successes,
        },
        upload_session_token,
        x_fab_ds=x_fab_ds,
    )


def post_parse_callback_sync(
    result: dict[str, Any],
    upload_session_token: str,
    callback_url: str,
    *,
    log_tag: str = "PARSE",
    timeout: int = 120,
    x_fab_ds: str = "",
) -> None:
    if not callback_url:
        logger.error("[%s] 未配置回调地址 sync_base_url / *_sync_callback_url", log_tag)
        return

    payload = format_parse_callback_payload(
        result,
        upload_session_token,
        module=log_tag,
        x_fab_ds=x_fab_ds,
    )
    headers = {"X-Fab-Ds": x_fab_ds} if x_fab_ds else None
    try:
        response = requests.post(callback_url, json=payload, headers=headers, timeout=timeout)
        logger.info(
            "[%s] 回调完成 url=%s status=%s uploadSessionToken=%s X-Fab-Ds=%s success=%s",
            log_tag,
            callback_url,
            response.status_code,
            upload_session_token,
            x_fab_ds,
            payload.get("success"),
        )
        if response.status_code >= 400:
            logger.error(
                "[%s] 回调失败 status=%s body=%s",
                log_tag,
                response.status_code,
                response.text[:500],
            )
    except Exception:
        logger.exception(
            "[%s] 回调请求异常 url=%s uploadSessionToken=%s",
            log_tag,
            callback_url,
            upload_session_token,
        )


async def run_sync_task_with_callback(
    sync_fn: Callable[[], dict[str, Any]],
    upload_session_token: str,
    callback_url: str,
    *,
    log_tag: str = "PARSE",
    x_fab_ds: str = "",
) -> None:
    """在线程池中执行同步任务，完成后 POST 回调。"""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, sync_fn)
    except Exception as exc:
        logger.error("[%s] 后台任务异常\n%s", log_tag, traceback.format_exc())
        result = make_task_error_response(f"算法调用失败: {exc}", detail=str(exc))

    await loop.run_in_executor(
        None,
        partial(
            post_parse_callback_sync,
            result,
            upload_session_token,
            callback_url,
            log_tag=log_tag,
            x_fab_ds=x_fab_ds,
        ),
    )
