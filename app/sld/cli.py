#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SLD 校验 CLI：由 FastAPI 子进程调用，读取 exec_config.json 并写 result JSON。"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python -m app.sld.cli <exec_config.json>", file=sys.stderr)
        sys.exit(2)

    config_path = Path(sys.argv[1])
    try:
        with open(config_path, encoding="utf-8") as f:
            params = json.load(f)
    except Exception as e:
        print(f"无法读取配置: {e}", file=sys.stderr)
        sys.exit(1)

    mission_start_time = params.get("mission_start_time", "")
    out_dir = config_path.parent
    result_path = out_dir / f"result_{mission_start_time}.json"

    # 保证项目根在 path（子进程工作目录可能为任意）
    root = Path(__file__).resolve().parent.parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        from app.sld.checker import run_sld_check

        params["cache_folder"] = str(out_dir)
        result = run_sld_check(params)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(0)
    except Exception as e:
        err = {
            "code": 400,
            "message": f"算法调用失败: {str(e)}",
            "success": False,
            "data": [{"errors": [str(e)]}],
        }
        result_path.write_text(json.dumps(err, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit(1)


if __name__ == "__main__":
    main()
