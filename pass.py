"""
ELD DXF 图纸解析脚本
解析 DXF 文件中的设备图块属性，并将结果写入 Excel 文件。

解析规则与 ELD 校验接口（dxf_parser.py）保持一致：
  - 只处理 INSERT（块引用）实体
  - 可按图层过滤（可选）
  - 只处理包含 TOOL_ID 属性的图块
  - TOOL_ID 若以 ^ 开头则去除前缀
  - 提取 TOOL_ID / OWNER / EQU.GROUP / VENDOR / MODEL / BAY_LOCATION / RECORDS 等属性
  - 同时记录图块固有信息：块名、图层、旋转角度、颜色、插入点、中心点、句柄

用法：
    python eld_dxf_to_excel.py <dxf文件路径> [输出excel路径] [--layers 图层1 图层2 ...]

示例：
    python eld_dxf_to_excel.py ./drawing.dxf
    python eld_dxf_to_excel.py ./drawing.dxf ./output.xlsx
    python eld_dxf_to_excel.py ./drawing.dxf ./output.xlsx --layers ELD ELD-EQUIP
"""

import sys
import argparse
import traceback
from pathlib import Path
from datetime import datetime

import ezdxf
from ezdxf import bbox
import pandas as pd


# ─────────────────────────────── 解析核心 ────────────────────────────────── #

def parse_eld_dxf(dxf_path: str, target_layers: list[str] | None = None) -> list[dict]:
    """
    解析 ELD DXF 文件，提取所有包含 TOOL_ID 属性的 INSERT 块。

    规则与 dxf_parser.parse_dxf 保持一致：
      1. 仅处理 INSERT 实体
      2. 若指定 target_layers，则跳过不在列表中的图层
      3. 块不存在于文档中则跳过
      4. TOOL_ID 为空则跳过
      5. TOOL_ID 去除开头的 ^ 符号

    :param dxf_path:      DXF 文件路径
    :param target_layers: 图层过滤列表，None 表示不过滤
    :return:              设备属性字典列表
    """
    print(f"[{datetime.now():%H:%M:%S}] 开始读取 DXF：{dxf_path}")
    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        raise RuntimeError(f"DXF 文件读取失败：{e}") from e

    msp = doc.modelspace()
    records: list[dict] = []

    skipped_no_tool_id = 0
    skipped_layer = 0
    skipped_no_block = 0

    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue

        # ── 图层过滤 ──────────────────────────────────────────────────────── #
        if target_layers and str(entity.dxf.layer) not in target_layers:
            skipped_layer += 1
            continue

        # ── 块定义检查 ────────────────────────────────────────────────────── #
        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            skipped_no_block += 1
            continue

        # ── 提取所有 ATTRIB 属性 ──────────────────────────────────────────── #
        attrs: dict[str, str] = {}
        for attr in entity.attribs:
            if hasattr(attr, 'dxf') and hasattr(attr.dxf, 'tag') and hasattr(attr.dxf, 'text'):
                tag = str(attr.dxf.tag).strip().upper()
                text = str(attr.dxf.text).strip() if attr.dxf.text else ''
                attrs[tag] = text

        # ── 必须包含非空 TOOL_ID ──────────────────────────────────────────── #
        if "TOOL_ID" not in attrs or not attrs["TOOL_ID"]:
            skipped_no_tool_id += 1
            continue

        # 去除 TOOL_ID 开头的 ^ 前缀
        tool_id = attrs["TOOL_ID"]
        if tool_id.startswith('^'):
            tool_id = tool_id[1:].strip()
        else:
            tool_id = tool_id.strip()

        # ── 计算中心点（包围盒）────────────────────────────────────────────── #
        try:
            bb = bbox.extents([entity], fast=False)
            if bb is not None:
                center_x = (bb.extmin.x + bb.extmax.x) / 2
                center_y = (bb.extmin.y + bb.extmax.y) / 2
            else:
                center_x = entity.dxf.insert.x
                center_y = entity.dxf.insert.y
        except Exception:
            center_x = entity.dxf.insert.x
            center_y = entity.dxf.insert.y

        # ── 组装记录 ──────────────────────────────────────────────────────── #
        # OWNER 优先，兼容 EQU.GROUP 字段
        owner = attrs.get("OWNER", '') or attrs.get("EQU.GROUP", '')

        record = {
            # ── 业务属性 ──────────────────────────────────────────────────── #
            "TOOL_ID":        tool_id,
            "OWNER":          owner,
            "VENDOR":         attrs.get("VENDOR", ""),
            "MODEL":          attrs.get("MODEL", ""),
            "BAY_LOCATION":   attrs.get("BAY_LOCATION", ""),
            "RECORDS":        attrs.get("RECORDS", ""),
            # ── 其他自定义属性（非固定字段） ─────────────────────────────── #
            "ALL_ATTRS":      str({k: v for k, v in attrs.items()
                                   if k not in ("TOOL_ID", "OWNER", "EQU.GROUP",
                                                "VENDOR", "MODEL", "BAY_LOCATION", "RECORDS")}),
            # ── 固有属性 ──────────────────────────────────────────────────── #
            "CAD_BLOCK_NAME": block_name,
            "LAYER":          str(entity.dxf.layer),
            "ANGLE":          round(float(entity.dxf.rotation)
                                    if hasattr(entity.dxf, 'rotation') else 0.0, 4),
            "TRUE_COLOR":     int(entity.dxf.color)
                              if hasattr(entity.dxf, 'color') else 0,
            "INSERT_X":       round(float(entity.dxf.insert.x), 4),
            "INSERT_Y":       round(float(entity.dxf.insert.y), 4),
            "INSERT_Z":       round(float(entity.dxf.insert.z), 4),
            "CENTER_X":       round(float(center_x), 4),
            "CENTER_Y":       round(float(center_y), 4),
            "CAD_BLOCK_ID":   str(entity.dxf.handle),
        }
        records.append(record)

    print(f"  解析完成：共 {len(records)} 个设备图块")
    print(f"  跳过（无TOOL_ID）：{skipped_no_tool_id}  跳过（图层过滤）：{skipped_layer}  "
          f"跳过（块不存在）：{skipped_no_block}")
    return records


# ─────────────────────────────── 写 Excel ────────────────────────────────── #

COLUMN_HEADERS = {
    "TOOL_ID":        "设备编号 (TOOL_ID)",
    "OWNER":          "所属分组 (OWNER/EQU.GROUP)",
    "VENDOR":         "供应商 (VENDOR)",
    "MODEL":          "型号 (MODEL)",
    "BAY_LOCATION":   "Bay位置 (BAY_LOCATION)",
    "RECORDS":        "记录 (RECORDS)",
    "ALL_ATTRS":      "其他属性",
    "CAD_BLOCK_NAME": "图块名称",
    "LAYER":          "图层",
    "ANGLE":          "旋转角度",
    "TRUE_COLOR":     "颜色号",
    "INSERT_X":       "插入点X",
    "INSERT_Y":       "插入点Y",
    "INSERT_Z":       "插入点Z",
    "CENTER_X":       "中心点X",
    "CENTER_Y":       "中心点Y",
    "CAD_BLOCK_ID":   "图块句柄 (Handle)",
}


def write_to_excel(records: list[dict], output_path: str, dxf_path: str) -> None:
    """将解析结果写入 Excel，包含设备列表和统计摘要两个 Sheet。"""
    df = pd.DataFrame(records)

    if df.empty:
        print("[警告] 未解析到任何设备，Excel 将为空表。")
        df = pd.DataFrame(columns=list(COLUMN_HEADERS.keys()))

    # 按列顺序排列
    ordered_cols = [c for c in COLUMN_HEADERS if c in df.columns]
    df = df[ordered_cols]
    df = df.rename(columns=COLUMN_HEADERS)

    # ── 统计摘要 ─────────────────────────────────────────────────────────── #
    summary_rows = [
        ["源文件",    str(dxf_path)],
        ["解析时间",  datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["设备总数",  len(records)],
        ["图层数",    df[COLUMN_HEADERS["LAYER"]].nunique() if records else 0],
        ["分组数",    df[COLUMN_HEADERS["OWNER"]].nunique() if records else 0],
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["项目", "值"])

    # 按图层统计
    if records:
        layer_stat = (df.groupby(COLUMN_HEADERS["LAYER"])
                        .size()
                        .reset_index(name="设备数量")
                        .rename(columns={COLUMN_HEADERS["LAYER"]: "图层"}))
    else:
        layer_stat = pd.DataFrame(columns=["图层", "设备数量"])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Sheet1：设备列表
        df.to_excel(writer, sheet_name="设备列表", index=False)
        _auto_column_width(writer.sheets["设备列表"], df)

        # Sheet2：统计摘要
        summary_df.to_excel(writer, sheet_name="统计摘要", index=False, startrow=0)
        layer_stat.to_excel(writer, sheet_name="统计摘要", index=False, startrow=len(summary_df) + 2)
        _auto_column_width(writer.sheets["统计摘要"], summary_df)

    print(f"[{datetime.now():%H:%M:%S}] Excel 已写入：{output_path}")


def _auto_column_width(ws, df: pd.DataFrame, min_width: int = 12, max_width: int = 60) -> None:
    """自动调整列宽。"""
    for i, col in enumerate(df.columns, start=1):
        col_letter = ws.cell(row=1, column=i).column_letter
        max_len = max(
            len(str(col)),
            df[col].astype(str).str.len().max() if not df.empty else 0,
        )
        ws.column_dimensions[col_letter].width = min(max(max_len + 2, min_width), max_width)


# ────────────────────────────────── CLI ──────────────────────────────────── #

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="解析 ELD DXF 图纸，将图块属性写入 Excel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("dxf", help="DXF 文件路径")
    p.add_argument("output", nargs="?", help="输出 Excel 路径（可选，默认同目录同名 .xlsx）")
    p.add_argument(
        "--layers", nargs="*", metavar="LAYER",
        help="仅解析指定图层的图块（不指定则解析全部图层）",
    )
    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    dxf_path = Path(args.dxf)
    if not dxf_path.exists():
        print(f"[错误] DXF 文件不存在：{dxf_path}", file=sys.stderr)
        sys.exit(1)

    # 输出路径：默认同目录同名 .xlsx
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = dxf_path.with_suffix(".xlsx")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    target_layers = args.layers if args.layers else None
    if target_layers:
        print(f"图层过滤：{target_layers}")

    try:
        records = parse_eld_dxf(str(dxf_path), target_layers=target_layers)
        write_to_excel(records, str(output_path), str(dxf_path))
        print(f"\n完成！共导出 {len(records)} 条设备记录 -> {output_path}")
    except Exception:
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
