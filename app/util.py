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


def _split_fid_rows(data: dict[str, Any]) -> dict[str, list[Any]]:
    interface_errors: list[Any] = []
    interface_successes: list[Any] = []
    field_errors: list[Any] = []
    field_successes: list[Any] = []

    for item in data.get("interfaces") or []:
        if not isinstance(item, dict):
            continue
        if _item_has_errors(item):
            interface_errors.append(item)
        else:
            interface_successes.append(item)

    for item in data.get("field") or []:
        if not isinstance(item, dict):
            continue
        if _item_has_errors(item):
            field_errors.append(item)
        else:
            field_successes.append(item)

    return {
        "interfaceErrors": interface_errors,
        "fieldErrors": field_errors,
        "interfaceSuccesses": interface_successes,
        "fieldSuccesses": field_successes,
    }


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


def _empty_fid_callback_rows() -> dict[str, list[Any]]:
    return {
        "interfaceErrors": [],
        "fieldErrors": [],
        "interfaceSuccesses": [],
        "fieldSuccesses": [],
    }


def format_parse_callback_payload(
    result: dict[str, Any],
    upload_session_token: str,
    *,
    module: str = "SLD",
    x_fab_ds: str = "",
) -> dict[str, Any]:
    """
    将各模块内部校验结果转为统一回调结构。

    FID 模块::

        {
            "uploadSessionToken": "...",
            "success": true/false,
            "errorMessage": "...",
            "interfaceErrors": [...],
            "fieldErrors": [...],
            "interfaceSuccesses": [...],
            "fieldSuccesses": [...],
        }

    其他模块（ELD/SLD）::

        {
            "uploadSessionToken": "...",
            "success": true/false,
            "errorMessage": "...",
            "errors": [...],
            "successes": [...],
        }

    ``success`` 语义：
    - 业务级（``code != 400``）：恒为 ``True``；是否校验通过看错误列表 / ``errorMessage``。
    - 系统级（``code == 400`` 或未捕获异常）：为 ``False``。
    """
    code = int(result.get("code") or 200)
    message = str(result.get("message") or "").strip()
    data = result.get("data")
    old_success = result.get("success")
    module_upper = (module or "SLD").upper()
    is_fid = module_upper == "FID"

    if code == 400 or (old_success is None and result.get("traceback")):
        if is_fid:
            fid_rows = _empty_fid_callback_rows()
            fid_rows["interfaceErrors"] = _system_error_rows(result)
            return _attach_callback_context(
                {
                    "success": False,
                    "errorMessage": message or "算法调用失败",
                    **fid_rows,
                },
                upload_session_token,
                x_fab_ds=x_fab_ds,
            )
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

    if is_fid and isinstance(data, dict):
        fid_rows = _split_fid_rows(data)
        has_business_errors = (
            old_success is False
            or bool(fid_rows["interfaceErrors"])
            or bool(fid_rows["fieldErrors"])
        )
        return _attach_callback_context(
            {
                "success": True,
                "errorMessage": (message or "校验失败") if has_business_errors else (message or "调用成功"),
                **fid_rows,
            },
            upload_session_token,
            x_fab_ds=x_fab_ds,
        )

    if isinstance(data, list):
        errors, successes = _split_list_rows(data)
    else:
        errors, successes = [], []

    has_business_errors = old_success is False or bool(errors)
    return _attach_callback_context(
        {
            "success": True,
            "errorMessage": (message or "校验失败") if has_business_errors else (message or "调用成功"),
            "errors": (
                errors
                if errors
                else (list(data) if has_business_errors and isinstance(data, list) else [])
            ),
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
