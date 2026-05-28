#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地测试专用：不执行 SLD **规范性校验**（specrules，含 ID_EQU/唯一性/文件名等 error），
直接走解析 → 柱网 → **变更校验** → 组装成功响应。

**不修改** `checker` / `validators` 等业务代码：通过在导入 `run_sld_check` **之前**
替换 `app.sld.validators.run_spec_checks` 为空实现实现。

用法（项目根目录）:
  python -m app.sld.test.run_sld_skip_specs --config exec_config_sld_patched.json
  python -m app.sld.test.run_sld_skip_specs --config exec_config_sld_patched.json -o out.json

注意：生产 / CI 请勿使用；仅用于本地对比变更(diff)行为。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _noop_run_spec_checks(ctx, devices):  # noqa: ANN001
    return []


def main() -> int:
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    ap = argparse.ArgumentParser(description="SLD 测试：跳过规范性校验，仅看解析+变更结果")
    ap.add_argument(
        "--config",
        "-c",
        type=Path,
        default=root / "exec_config_sld_patched.json",
        help="exec_config JSON（含 equipmentList / eldSubEquipmentList 等）",
    )
    ap.add_argument(
        "--dxf",
        type=Path,
        default=None,
        help="覆盖配置中的 DXF（默认用配置 file / file_path 或 YMTC 样例路径）",
    )
    ap.add_argument(
        "--out",
        "-o",
        type=Path,
        default=None,
        help="结果 JSON 路径（默认打印 success 与 data 条数）",
    )
    args = ap.parse_args()

    cfg_path = args.config
    if not cfg_path.is_file():
        print(f"配置不存在: {cfg_path}", file=sys.stderr)
        return 1

    with open(cfg_path, encoding="utf-8") as f:
        params = json.load(f)

    if args.dxf:
        params["file_path"] = str(args.dxf.resolve())
    else:
        raw = params.get("file_path") or params.get("file") or ""
        p = Path(raw)
        if not p.is_absolute():
            p = (root / p).resolve()
        params["file_path"] = str(p)

    work = root / "app" / "sld" / "work" / "skip_specs_test"
    work.mkdir(parents=True, exist_ok=True)
    params["cache_folder"] = str(work)
    params["mission_start_time"] = params.get("mission_start_time") or time.strftime(
        "%Y%m%d_%H%M%S"
    )

    import app.sld.validators as _sld_validators

    _sld_validators.run_spec_checks = _noop_run_spec_checks  # type: ignore[assignment]

    from app.sld.checker import run_sld_check

    t0 = time.perf_counter()
    result = run_sld_check(params)
    elapsed = time.perf_counter() - t0

    envelope = {
        "elapsed_sec": round(elapsed, 3),
        "skipped": "run_spec_checks (规范性校验已跳过，仅测试)",
        "response": result,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"written: {args.out}")

    ok = result.get("success")
    data = result.get("data") or []
    print(f"elapsed_sec={elapsed:.2f} success={ok}")
    if ok and isinstance(data, list) and data and isinstance(data[0], dict):
        rows = data if isinstance(data, list) else []
        print(f"data_rows={len(rows)}")
        if rows:
            sample = rows[0]
            print(
                f"sample operation={sample.get('operation')} "
                f"diffContent={len(sample.get('diffContent') or [])}"
            )
    elif not ok and isinstance(data, list):
        print(f"error_rows={len(data)} (规范性已跳过，若有 error 来自其它逻辑请检查)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
