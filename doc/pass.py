#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动测试 FID 校验回调接口 POST equipment/fidFile/onFidParseComplete。

用法（项目根目录）::

    python tests/test_post_onFidParseComplate.py
    python tests/test_post_onFidParseComplate.py --url http://10.22.64.89:8080/efms/equipment/fidFile/onFidParseComplete
    python tests/test_post_onFidParseComplate.py --result doc/result.json --token test-token --x-fab-ds fab1
    python tests/test_post_onFidParseComplate.py --scenario error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.fid_config import build_fid_callback_url
from app.util import format_parse_callback_payload


def _sample_success_result() -> dict[str, Any]:
    return {
        "code": 200,
        "message": "调用成功",
        "success": True,
        "data": {
            "interfaces": [
                {
                    "uniCode": "D-IPA;FAB1F2;WS03;04",
                    "operation": "update",
                    "detail": "测试变更项",
                    "diffContent": [],
                }
            ],
            "field": [],
            "interfaces_add": 0,
            "interfaces_update": 1,
            "interfaces_delete": 0,
            "fields_add": 0,
            "fields_update": 0,
            "fields_delete": 0,
            "interfaces_num": 1,
            "field_nums": 0,
        },
    }


def _sample_error_result() -> dict[str, Any]:
    return {
        "code": 200,
        "message": "调用成功",
        "success": False,
        "data": {
            "interfaces": [
                {
                    "uniCode": "D-IPA;FAB1F2;WS03;04",
                    "operation": "update",
                    "errors": [
                        {
                            "errorName": "必填项缺失",
                            "errorType": "error",
                            "errorDescription": "测试错误项",
                        }
                    ],
                }
            ],
            "field": [],
            "interfaces_add": 0,
            "interfaces_update": 0,
            "interfaces_delete": 0,
            "fields_add": 0,
            "fields_update": 0,
            "fields_delete": 0,
            "interfaces_num": 1,
            "field_nums": 0,
        },
    }


def build_fid_callback_payload(
    result: dict[str, Any],
    *,
    upload_session_token: str = "test-upload-session-token",
    x_fab_ds: str = "",
) -> dict[str, Any]:
    """与线上回调一致：内部校验结果 → 统一回调 body。"""
    return format_parse_callback_payload(
        result,
        upload_session_token,
        module="FID",
        x_fab_ds=x_fab_ds,
    )


def post_fid_parse_complete_callback(
    payload: dict[str, Any],
    *,
    url: str | None = None,
    x_fab_ds: str = "",
    timeout: int = 120,
) -> requests.Response:
    """
    POST FID 校验完成回调。

    :param payload: 回调 JSON body（建议使用 ``build_fid_callback_payload`` 生成）
    :param url: 回调地址，默认读取 ``global_config/env`` 中 FID 配置
    :param x_fab_ds: 写入请求头 ``X-Fab-Ds``（body 无该字段时补充）
    :param timeout: 请求超时秒数
    """
    callback_url = (url or build_fid_callback_url()).strip()
    if not callback_url:
        raise ValueError("回调 URL 为空，请配置 sync_base_url / fid_sync_callback_url 或使用 --url")

    header_fab_ds = x_fab_ds or str(payload.get("X-Fab-Ds") or "")
    headers = {"Content-Type": "application/json"}
    if header_fab_ds:
        headers["X-Fab-Ds"] = header_fab_ds
        payload.setdefault("X-Fab-Ds", header_fab_ds)

    return requests.post(callback_url, json=payload, headers=headers, timeout=timeout)


def _load_result_file(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(description="测试 POST FID 回调 onFidParseComplete")
    parser.add_argument(
        "--url",
        default="",
        help="回调完整 URL，默认 env 中 sync_base_url + fid_sync_callback_url",
    )
    parser.add_argument("--token", default="test-upload-session-token", help="uploadSessionToken")
    parser.add_argument("--x-fab-ds", default="", help="X-Fab-Ds")
    parser.add_argument(
        "--result",
        type=Path,
        default=None,
        help="内部校验结果 JSON（如 doc/result.json），将自动转为回调 body",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=None,
        help="直接作为回调 body 的 JSON 文件（跳过 format_parse_callback_payload）",
    )
    parser.add_argument(
        "--scenario",
        choices=("success", "error"),
        default="success",
        help="未指定 --result/--payload 时使用的内置样例",
    )
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    if args.payload:
        payload = _load_result_file(args.payload)
    elif args.result:
        internal = _load_result_file(args.result)
        payload = build_fid_callback_payload(
            internal,
            upload_session_token=args.token,
            x_fab_ds=args.x_fab_ds,
        )
    else:
        internal = _sample_success_result() if args.scenario == "success" else _sample_error_result()
        payload = build_fid_callback_payload(
            internal,
            upload_session_token=args.token,
            x_fab_ds=args.x_fab_ds,
        )

    callback_url = args.url or build_fid_callback_url()
    print(f"POST {callback_url}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        response = post_fid_parse_complete_callback(
            payload,
            url=callback_url or None,
            x_fab_ds=args.x_fab_ds,
            timeout=args.timeout,
        )
    except requests.RequestException as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        return 1

    print(f"\nHTTP {response.status_code}")
    print(response.text[:2000])
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
