#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLD DXF 读取测试脚本。

字段与 app/sld/doc/sld_check.md 一致：
  §4.4 业务属性：ID_EQU、ID_EquSubShort、OWNER、VENDOR、MODEL、BAY_LOCATION、RECORDS、TOOL_ID（输出 tool_id）
  §4.5 固有属性：block_name、layer、angle、true_color、insert_point_x/y/z、center_point_x/y/z、block_id
  §6  纯解析阶段 grid_x / grid_y 为空（柱网匹配由 checker 写入）

用法（在项目根目录，且已配置 PYTHONPATH 或安装为包）:
  python app/sld/read_sld_dxf_test.py /path/to/YMTC^SLD^FAB1^F1.dxf
  python app/sld/read_sld_dxf_test.py ./foo.dxf --layers "100_DBS 5K,OTHER"
  python app/sld/read_sld_dxf_test.py ./foo.dxf --json-out ./out.json
  python app/sld/read_sld_dxf_test.py ./foo.dxf --expect-sld-name
  python app/sld/read_sld_dxf_test.py ./foo.dxf --bbox-slow   # 包围盒 fast=False，更准更慢
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.sld.parser import parse_sld_dxf, sld_filename_stem_ok


def _export_item(d: Any) -> Dict[str, Any]:
    """
    按 sld_check.md 约定顺序输出单条记录（snake_case，与 eqp_data 逻辑字段对齐）。
    """
    ad = asdict(d)
    return {
        # §4.4 业务
        "id_equ": ad.get("id_equ"),
        "id_equ_sub_short": ad.get("id_equ_sub_short"),
        "tool_id": ad.get("tool_id"),
        "owner": ad.get("owner"),
        "vendor": ad.get("vendor"),
        "model": ad.get("model"),
        "bay_location": ad.get("bay_location"),
        "records": ad.get("records"),
        # §6 柱网（纯解析为空）
        "grid_x": ad.get("grid_x"),
        "grid_y": ad.get("grid_y"),
        # §4.5 固有
        "block_name": ad.get("block_name"),
        "layer": ad.get("layer"),
        "angle": ad.get("angle"),
        "true_color": ad.get("true_color"),
        "insert_point_x": ad.get("insert_point_x"),
        "insert_point_y": ad.get("insert_point_y"),
        "insert_point_z": ad.get("insert_point_z"),
        "center_point_x": ad.get("center_point_x"),
        "center_point_y": ad.get("center_point_y"),
        "center_point_z": ad.get("center_point_z"),
        "block_id": ad.get("block_id"),
        # 排障：图块上出现的 ATTRIB tag（大写）
        "raw_attrib_tags": ad.get("raw_attrib_tags") or [],
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="SLD DXF 解析测试（字段见 app/sld/doc/sld_check.md §4.4 / §4.5）"
    )
    p.add_argument("dxf", type=Path, help="SLD 用 .dxf 路径")
    p.add_argument(
        "--layers",
        type=str,
        default="",
        help="逗号分隔图层白名单；留空则解析全部 INSERT（见 sld_check.md §3.2）",
    )
    p.add_argument("--json-out", type=Path, default=None, help="将完整结果写入 JSON")
    p.add_argument(
        "--expect-sld-name",
        action="store_true",
        help="若设置，则当文件名不符合 *^SLD^*^* 时在 stderr 打警告",
    )
    p.add_argument(
        "--bbox-slow",
        action="store_true",
        help="包围盒使用 fast=False（更慢、更准）",
    )
    args = p.parse_args(argv)

    stem = args.dxf.stem
    if args.expect_sld_name and not sld_filename_stem_ok(stem):
        print(f"[WARN] 文件名不符合 SLD 约定: {stem}", file=sys.stderr)

    layer_list: Optional[List[str]] = None
    if args.layers.strip():
        layer_list = [x.strip() for x in args.layers.split(",") if x.strip()]

    bbox_fast = not args.bbox_slow
    t0 = datetime.now()
    try:
        devices = parse_sld_dxf(args.dxf, target_layers=layer_list, bbox_fast=bbox_fast)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1
    elapsed = (datetime.now() - t0).total_seconds()

    items = [_export_item(d) for d in devices]
    payload = {
        "dxf": str(args.dxf.resolve()),
        "stem": stem,
        "layer_filter": layer_list,
        "bbox_fast": bbox_fast,
        "count": len(items),
        "elapsed_sec": round(elapsed, 4),
        "items": items,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
        print(f"\n已写入: {args.json_out}", file=sys.stderr)

    print(f"\n共 {len(items)} 条有效 INSERT，耗时 {elapsed:.4f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
