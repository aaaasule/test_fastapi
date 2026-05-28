#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地测试 POST /api/sld_check（application/json）。

用法:
  cd 项目根目录
  python -m app.sld.test.sld_post
  python -m app.sld.test.sld_post --config app/sld/doc/sld_post_sample.json
  python -m app.sld.test.sld_post --url http://127.0.0.1:8080 --dxf /path/to/YMTC^SLD^FAB1^F1.dxf

依赖: requests（与项目其它 post 脚本一致）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def _default_sample_path() -> Path:
    return Path(__file__).resolve().parent.parent / "doc" / "sld_post_sample.json"


def _load_config(path: Path | None) -> dict:
    p = path or _default_sample_path()
    if not p.is_file():
        raise FileNotFoundError(f"配置文件不存在: {p}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description="测试 SLD 校验接口 POST /api/sld_check (JSON)")
    ap.add_argument(
        "--config",
        type=Path,
        default="app/sld/doc/sld_post_sample.json",
        help=f"JSON 配置路径，默认 {_default_sample_path()}",
    )
    ap.add_argument("--url", type=str, default="http://127.0.0.1:8000", help="服务根地址，覆盖配置中的 base_url")
    ap.add_argument("--dxf", type=Path, default=None, help="本机 DXF 路径，覆盖配置中的 file")
    ap.add_argument("--timeout", type=int, default=3600, help="请求超时秒数（大图纸建议调大）")
    args = ap.parse_args()

    try:
        import requests
    except ImportError:
        print("请先安装: pip install requests", file=sys.stderr)
        return 1

    cfg = _load_config(args.config)
    root = _project_root()

    base_url = (args.url or cfg.get("base_url") or "http://127.0.0.1:8000").rstrip("/")
    api_url = f"{base_url}/api/sld_check"

    sld_dir = (root / "app" / "sld").resolve()
    file_field = cfg.get("file") or "local:doc/YMTC^SLD^FAB1^F1.dxf"
    if args.dxf is not None:
        dxf_path = args.dxf.resolve()
        if not dxf_path.is_file():
            print(f"DXF 不存在: {dxf_path}", file=sys.stderr)
            return 1
        try:
            rel = dxf_path.relative_to(sld_dir)
            file_field = f"local:{rel.as_posix()}"
        except ValueError:
            if not str(dxf_path).startswith(str(sld_dir)):
                print(f"本机 DXF 须在 app/sld 下: {dxf_path}", file=sys.stderr)
                return 1
            file_field = f"local:{dxf_path}"
    elif file_field.startswith("local:"):
        local_part = file_field[len("local:") :].strip()
        check = (sld_dir / local_part).resolve() if not Path(local_part).is_absolute() else Path(local_part).resolve()
        if not check.is_file():
            print(f"DXF 不存在: {check}", file=sys.stderr)
            return 1

    payload = {
        "company": cfg.get("company", {}),
        "building": cfg.get("building", {}),
        "buildingLevel": cfg.get("buildingLevel", {}),
        "equipmentList": cfg.get("equipmentList", []),
        "equipmentGroupList": cfg.get("equipmentGroupList", []),
        "eldSubEquipmentList": cfg.get("eldSubEquipmentList", []),
        "layerList": cfg.get("layerList", []),
        "gridList": cfg.get("gridList", []),
        "fab": cfg.get("fab", {}),
        "file": file_field,
    }

    print(f"POST {api_url}")
    print(f"JSON file: {payload['file']}")

    response = requests.post(api_url, json=payload, timeout=args.timeout)

    if response.status_code == 200:
        out = response.json()
        print(json.dumps(out, indent=2, ensure_ascii=False))
        out_path = root / "app" / "sld" / "doc" / "sld_post_last_response.json"
        try:
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n已写入: {out_path}", file=sys.stderr)
        except OSError as e:
            print(f"写入响应文件失败: {e}", file=sys.stderr)
        return 0

    print(f"HTTP {response.status_code}", file=sys.stderr)
    print(response.text, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
