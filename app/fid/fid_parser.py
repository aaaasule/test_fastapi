# dxf_parser.py
import gc
import json
import mmap
import os
import datetime
import sys
from pathlib import Path
from typing import Any, Iterator, List

import ezdxf
from ezdxf.addons import iterdxf
from ezdxf.lldxf.validator import is_binary_dxf_file, is_dxf_file

from app.fid.models import Equipment, FileInfo
from app.fid.utils.check_device import check_which_device

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

current_file = Path(__file__).resolve()
root_dir = current_file.parent
while root_dir.name != "app" and root_dir.parent != root_dir:
    root_dir = root_dir.parent

if root_dir.name == "app":
    project_root = root_dir.parent
else:
    project_root = current_file.parent.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.config.fid_config import FID_REQUIRED_FIELDS

# 设为 1 时强制完整加载 Drawing（兼容需 doc.blocks 的场景）
ENV_FORCE_FULL_DXF_LOAD = "FID_DXF_USE_FULL_LOAD"


def read_dxf_streaming(dxf_path: str | Path, encoding: str | None = None) -> ezdxf.document.Drawing:
    """完整加载 DXF（二进制用 mmap）。用于 iterdxf 不可用时的回退。"""
    from ezdxf.document import Drawing
    from ezdxf.filemanagement import dxf_file_info
    from ezdxf.lldxf.tagger import binary_tags_loader
    from ezdxf.tools.codepage import is_supported_encoding

    path = Path(dxf_path)
    path_str = str(path)

    if is_binary_dxf_file(path_str):
        with open(path_str, "rb") as fp:
            with mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                doc = Drawing.load(binary_tags_loader(mm))
        doc.filename = path_str
        return doc

    if not is_dxf_file(path_str):
        raise IOError(f"不是有效的 DXF 文件: {path_str}")

    info = dxf_file_info(path_str)
    text_encoding = encoding or info.encoding
    with open(path_str, mode="rt", encoding=text_encoding, errors="surrogateescape") as fp:
        doc = Drawing.read(fp)
    doc.filename = path_str
    if encoding is not None and is_supported_encoding(encoding):
        doc.encoding = encoding
    return doc


def can_use_iterdxf(dxf_path: str | Path) -> bool:
    """iterdxf 仅适用于可 seek 的 ASCII/文本 DXF。"""
    path_str = str(Path(dxf_path))
    if os.environ.get(ENV_FORCE_FULL_DXF_LOAD, "").strip() in ("1", "true", "yes"):
        return False
    return is_dxf_file(path_str) and not is_binary_dxf_file(path_str)


def clean_unicode_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    return "".join(char for char in text if not ("\ud800" <= char <= "\udfff"))


def _extract_insert_attrs(entity: Any) -> dict[str, Any]:
    attrs: dict[str, Any] = {}
    for attr in entity.attribs:
        if hasattr(attr, "dxf") and hasattr(attr.dxf, "tag") and hasattr(attr.dxf, "text"):
            tag = str(attr.dxf.tag).strip().upper()
            raw_text = attr.dxf.text if attr.dxf.text else ""
            attrs[tag] = clean_unicode_text(str(raw_text).strip())
    return attrs


def _process_insert_entity(
    entity: Any,
    filename: str,
    equipments: dict[str, list],
    id_unique: set[str],
    *,
    doc: ezdxf.document.Drawing | None = None,
) -> None:
    # iterdxf 在 types 含 INSERT 时会一并加载 SEQEND/ATTRIB，孤立 SEQEND 也可能被 yield
    if entity.dxftype() != "INSERT":
        return

    block_name = entity.dxf.name
    if doc is not None and block_name not in doc.blocks:
        return

    attrs = _extract_insert_attrs(entity)
    if "REMARK1" in attrs or not attrs:
        return

    attrs["cad_block_name"] = block_name
    attrs["layer"] = entity.dxf.layer
    attrs["angle"] = float(entity.dxf.rotation) if hasattr(entity.dxf, "rotation") else None
    attrs["true_color"] = int(entity.dxf.color) if hasattr(entity.dxf, "color") else None
    attrs["insert_point_x"] = round(float(entity.dxf.insert.x), 4)
    attrs["insert_point_y"] = round(float(entity.dxf.insert.y), 4)
    attrs["insert_point_z"] = round(float(entity.dxf.insert.z), 4)
    attrs["center_point_x"] = round(float(entity.dxf.insert.x), 4)
    attrs["center_point_y"] = round(float(entity.dxf.insert.y), 4)
    attrs["cad_block_id"] = str(entity.dxf.handle)

    device = check_which_device(attrs, filename)
    if device == "TAKEOFF":
        attrs["distribution_box"] = False
    else:
        attrs["distribution_box"] = True

    attrs = {k.upper(): v for k, v in attrs.items()}

    if device is None:
        print(f"device无法识别{attrs=}")
        return
    if "ID" not in attrs and "INTERFACE_CODE" not in attrs and "ID_SHORT" not in attrs:
        return

    unique_key = (
        f"{attrs.get('INTERFACE_CODE') or attrs.get('ID_SHORT') or attrs.get('ID')}_"
        f"{attrs['CAD_BLOCK_ID']}"
    )
    if unique_key in id_unique:
        print("解析遇到相同 id", unique_key)
        raise Exception(unique_key)
    id_unique.add(unique_key)
    equipments[device].append(attrs)


def _iter_inserts_iterdxf(dxf_path: str | Path) -> Iterator[Any]:
    """仅解析 ENTITIES 中的 INSERT，不构建完整 Drawing。"""
    for entity in iterdxf.modelspace(str(dxf_path), types=["INSERT"]):
        if entity.dxftype() == "INSERT":
            yield entity


def _fid_parse_via_iterdxf(dxf_path: str, filename: str) -> dict[str, list]:
    equipments = {k: [] for k in FID_REQUIRED_FIELDS}
    id_unique: set[str] = set()
    for entity in _iter_inserts_iterdxf(dxf_path):
        _process_insert_entity(entity, filename, equipments, id_unique, doc=None)
    return equipments


def _fid_parse_via_drawing(dxf_path: str, filename: str) -> dict[str, list]:
    doc = read_dxf_streaming(dxf_path)
    try:
        equipments = {k: [] for k in FID_REQUIRED_FIELDS}
        id_unique: set[str] = set()
        for entity in doc.modelspace().query("INSERT"):
            _process_insert_entity(entity, filename, equipments, id_unique, doc=doc)
        return equipments
    finally:
        del doc
        gc.collect()


def fid_parse_dxf(dxf_path: str, filename: str, file_info: FileInfo = None) -> List[Equipment]:
    """
    解析 DXF，提取 INSERT 图块设备属性。

    文本 DXF 默认使用 ``ezdxf.addons.iterdxf`` 单遍迭代（低内存、跳过大段非 INSERT 实体）；
    二进制 DXF 或设置 ``FID_DXF_USE_FULL_LOAD=1`` 时回退为完整 ``Drawing`` 加载。
    """
    start_time = datetime.datetime.now()
    path = Path(dxf_path)

    try:
        if can_use_iterdxf(path):
            print("DXF 解析模式: iterdxf (仅 INSERT)")
            try:
                equipments = _fid_parse_via_iterdxf(str(path), filename)
            except (ezdxf.DXFAttributeError, ezdxf.DXFStructureError) as iter_exc:
                print(f"iterdxf 解析异常，回退完整 Drawing: {iter_exc}")
                equipments = _fid_parse_via_drawing(str(path), filename)
        else:
            print("DXF 解析模式: 完整 Drawing 加载")
            equipments = _fid_parse_via_drawing(str(path), filename)
    except IOError:
        raise ValueError(f"无法读取 DXF 文件: {dxf_path}")
    except ezdxf.DXFStructureError:
        raise ValueError(f"DXF 文件结构损坏: {dxf_path}")

    print(f"读取与解析耗时： {datetime.datetime.now() - start_time}")
    print(json.dumps({k: len(v) for k, v in equipments.items()}, ensure_ascii=False, indent=4))
    return equipments


if __name__ == "__main__":
    import time

    for file in Path("doc/").glob("*"):
        print(file)
        start_time1 = time.time()
        equipments = fid_parse_dxf(str(file), file.name)
        print(time.time() - start_time1)
        for device in equipments:
            for e in equipments[device]:
                if e.get("CAD_BLOCK_ID") == "18DBF2":
                    print("*******************")
                    print(e)
        print("接口解析耗时", time.time() - start_time1)
