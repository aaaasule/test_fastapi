# -*- coding: utf-8 -*-
"""跨模块通用工具：异步校验立即响应与结果回调。"""
from __future__ import annotations

import asyncio
import json
import re
import traceback
from collections.abc import Callable
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

import requests

from app.config import logger
from app.config.fid_config import SYNC_BASE_URL
from app.fid.utils.replace_nan_with_none import replace_nan_with_none
from app.fid.utils.snake_to_camel import snake_to_camel

_CALLBACK_PAYLOAD_DIR = Path(__file__).resolve().parent / "temp_debug" / "callback_payload"
_FID_CALLBACK_ROW_KEYS = (
    "interfaceErrors",
    "fieldErrors",
    "interfaceSuccesses",
    "fieldSuccesses",
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


def _deep_keys_to_camel(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            (snake_to_camel(k) if "_" in str(k) else k): _deep_keys_to_camel(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_deep_keys_to_camel(item) for item in obj]
    return obj


def _normalize_fid_flag(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return 1 if value.lower() == "true" else 0
    return value


def _normalize_fid_callback_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = _deep_keys_to_camel(replace_nan_with_none(row))
    for key in ("distributionBox", "locked"):
        if key in normalized:
            normalized[key] = _normalize_fid_flag(normalized[key])
    return normalized


def _prepare_fid_callback_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """FID 回调：camelCase、非法浮点清洗，并将布尔标记转为 0/1。"""
    prepared = replace_nan_with_none(payload)
    for key in _FID_CALLBACK_ROW_KEYS:
        rows = prepared.get(key)
        if not isinstance(rows, list):
            continue
        prepared[key] = [
            _normalize_fid_callback_row(row) if isinstance(row, dict) else row
            for row in rows
        ]
    return prepared


def _json_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """确保可被标准 JSON 解析（禁止 NaN/Infinity 与非原生类型）。"""
    return json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))


def _attach_callback_context(
    payload: dict[str, Any],
    upload_session_token: str,
    *,
    x_fab_ds: str = "",
) -> dict[str, Any]:
    out = dict(payload)
    out["uploadSessionToken"] = upload_session_token
    # X-Fab-Ds 通过 HTTP Header 传递；放入 Body 可能导致 Java 端严格反序列化失败
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
            error_message = message or "算法调用失败"
            return _attach_callback_context(
                {
                    "code": code,
                    "message": error_message,
                    "success": False,
                    "errorMessage": error_message,
                    **_empty_fid_callback_rows(),
                },
                upload_session_token,
                x_fab_ds=x_fab_ds,
            )
        return _attach_callback_context(
            {
                "success": False,
                "errorMessage": message or "算法调用失败",
                "errors": [],
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
        error_message = (message or "校验失败") if has_business_errors else (message or "调用成功")
        return _attach_callback_context(
            {
                "code": code,
                "message": error_message,
                "success": True,
                "errorMessage": error_message,
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


def _dump_callback_payload_to_file(
    payload: dict[str, Any],
    *,
    log_tag: str,
    upload_session_token: str,
) -> Path:
    """将回调 payload 写入 JSON 文件，便于排查。"""
    _CALLBACK_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_token = re.sub(r"[^\w\-]", "_", upload_session_token or "unknown")[:64]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = _CALLBACK_PAYLOAD_DIR / f"{log_tag.lower()}_{safe_token}_{ts}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return file_path


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
    if (log_tag or "").upper() == "FID":
        payload = _prepare_fid_callback_payload(payload)
    payload = _json_safe_payload(payload)

    headers = {"Content-Type": "application/json; charset=utf-8"}
    if x_fab_ds:
        headers["X-Fab-Ds"] = x_fab_ds
    try:
        logger.info("[%s] payload keys: %s", log_tag, list(payload.keys()))
        payload_file = _dump_callback_payload_to_file(
            payload,
            log_tag=log_tag,
            upload_session_token=upload_session_token,
        )
        logger.info("[%s] payload 已写入 %s", log_tag, payload_file)

        response = requests.post(
            callback_url,
            data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"),
            headers=headers,
            timeout=timeout,
        )
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
