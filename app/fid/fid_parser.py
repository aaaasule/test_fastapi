# dxf_parser.py
import json
import traceback
import datetime
import ezdxf
from typing import List
from app.fid.models import Equipment, FileInfo

from app.fid.utils.check_device import check_which_device

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（当前文件: app/fid/eld_check_cli.py -> 上两级到根目录）
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


#from app.config.fid_config import FID_REQUIRED_FIELDS

current_file = Path(__file__).resolve()
root_dir = current_file.parent
while root_dir.name != 'app' and root_dir.parent != root_dir:
    root_dir = root_dir.parent

if root_dir.name == 'app':
    project_root = root_dir.parent
else:
    #  fallback: 假设就在上一级
    project_root = current_file.parent.parent

# 3. 将项目根目录加入 Python 搜索路径
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 4. 现在可以直接导入，去掉 'app.config' 前缀
from app.config.fid_config import FID_REQUIRED_FIELDS
import chardet


def clean_unicode_text(text: str) -> str:
    """
    移除字符串中的无效 Unicode 代理字符 (Surrogates)，防止 UTF-8 编码报错。
    范围：\ud800 - \udfff
    """
    if not isinstance(text, str):
        return text
    # 方法：通过 encode/decode 忽略错误，或者手动过滤
    # 这里使用手动过滤保留其他字符
    return "".join(char for char in text if not ('\ud800' <= char <= '\udfff'))

def fid_parse_dxf(dxf_path: str, filename: str, file_info: FileInfo = None) -> List[Equipment]:
    """
    解析 DXF 文件，提取所有包含 'TOOL_ID' 属性的 INSERT 块（设备）。

    :param dxf_path: DXF 文件路径
    :param file_info: 文件信息（用于绑定到 Equipment）
    :return: Equipment 列表
    """
    start_time = datetime.datetime.now()

    def read_dxf_auto_encoding(dxf_path):

        print('开始读取dxf--')
        # 1. 读取原始字节
        with open(dxf_path, 'rb') as f:
            raw_data = f.read()

        # 2. 检测编码
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        confidence = detected['confidence']

        print(f"🔍 检测到编码: {encoding}, 置信度: {confidence:.2f}")

        # 3. 如果置信度低，或检测为 'ascii'，尝试更安全的候选编码
        candidates = []
        if confidence < 0.8 or encoding in ('ascii', 'ISO-8859-1', None):
            # 常见 DXF 编码候选：UTF-8（带/不带 BOM）、GBK、GB2312、Latin1
            candidates = ['utf-8-sig', 'gbk', 'gb2312', 'latin1', 'cp1252']
        else:
            candidates = [encoding, 'utf-8-sig', 'gbk']  # 主检测 + 常见备选

        # 4. 尝试按顺序加载，直到成功
        for enc in candidates:
            if enc is None:
                continue
            try:
                print(f"🔄 尝试使用编码: {enc}")
                doc = ezdxf.readfile(dxf_path, encoding=enc)
                print(f"✅ 成功读取！使用编码: {enc}")
                return doc

            except Exception as e:
                print(traceback.format_exc())
                doc = ezdxf.readfile(dxf_path, encoding='gbk')
                return doc

    # print(read_dxf_auto_encoding(dxf_path))
    # raise Exception
    try:
        doc = ezdxf.readfile(dxf_path)
        #doc = read_dxf_auto_encoding(dxf_path)
    except IOError:
        raise ValueError(f"无法读取 DXF 文件: {dxf_path}")
    except ezdxf.DXFStructureError:
        raise ValueError(f"DXF 文件结构损坏: {dxf_path}")

    msp = doc.modelspace()
    # equipments: List[Equipment] = []
    equipments = {
        k: [] for k in FID_REQUIRED_FIELDS
    }

    name = set()
    for entity_i, entity in enumerate(msp):
        # continue
        # print(entity.dxftype())

        #print(f"解析第{entity_i + 1}个实体")

        # 只处理 INSERT（块引用）
        if entity.dxftype() != "INSERT":
            continue

        # if str(entity.dxf.layer) not in ['PC-A-HF-100TO1']:
        #     print(f"{str(entity.dxf.layer)} 不在目标layers中 {'PC-A-HF-100TO1'}")
        #     continue

        # 获取块定义（用于检查是否含属性）
        block_name = entity.dxf.name
        if block_name not in doc.blocks:
            continue

        # 提取所有属性（ATTRIB）
        attrs = {}
        for attr in entity.attribs:

            if hasattr(attr, 'dxf') and hasattr(attr.dxf, 'tag') and hasattr(attr.dxf, 'text'):
                tag = str(attr.dxf.tag).strip().upper()
                #text = str(attr.dxf.text).strip() if attr.dxf.text else ''

                raw_text = attr.dxf.text if attr.dxf.text else ''
                text = clean_unicode_text(str(raw_text).strip())

                attrs[tag] = text

        # print(json.dumps(attrs, ensure_ascii=False, indent=4))

        if "REMARK1" in attrs:
            continue


        id_unique = set()
        # continue
        # 构建 Equipment 对象
        if len(attrs) > 0:
            # print(block_name)
            # 固有属性
            attrs['cad_block_name'] = block_name
            attrs['layer'] = entity.dxf.layer
            attrs['angle'] = float(entity.dxf.rotation) if hasattr(entity.dxf, 'rotation') else None
            attrs['true_color'] = int(entity.dxf.color) if hasattr(entity.dxf, 'color') else None
            attrs['insert_point_x'] = round(float(entity.dxf.insert.x), 4)
            attrs['insert_point_y'] = round(float(entity.dxf.insert.y), 4)
            attrs['insert_point_z'] = round(float(entity.dxf.insert.z), 4)
            attrs['center_point_x'] = round(float(entity.dxf.insert.x), 4)
            attrs['center_point_y'] = round(float(entity.dxf.insert.y), 4)
            attrs['cad_block_id'] = str(entity.dxf.handle)

            # print(attrs)
            # equipments.append(attrs)
            device = check_which_device(attrs, filename)

            if device == 'TAKEOFF':
                attrs['distribution_box'] = False
            else:
                attrs['distribution_box'] = True


            attrs = {k.upper(): v for k, v in attrs.items()}

            if device is None:
                print(f"device无法识别{attrs=}")
                continue
            if 'ID' not in attrs and 'INTERFACE_CODE' not in attrs and 'ID_SHORT' not in attrs:
                #print(f"ID不存在{attrs=}")
                continue

            equipments[device].append(attrs)

            if f"{attrs.get('INTERFACE_CODE') or  attrs.get('ID_SHORT') or attrs.get('ID')}_{attrs['CAD_BLOCK_ID']}" not in id_unique:
                id_unique.add(f"{attrs.get('INTERFACE_CODE') or  attrs.get('ID_SHORT') or attrs.get('ID')}_{attrs['CAD_BLOCK_ID']}")
            else:
                print(f"解析遇到相同 id", f"{attrs.get('INTERFACE_CODE') or  attrs.get('ID_SHORT') or attrs.get('ID')}_{attrs['CAD_BLOCK_ID']}")
                raise Exception
    print(json.dumps({k: len(v) for k, v in equipments.items()}, ensure_ascii=False, indent=4))
    print(f"解析文件耗时： {datetime.datetime.now() - start_time}")

    return equipments


if __name__ == '__main__':
    from pathlib import Path
    from app.fid.utils.parse_block_attributes import parse_block_attributes
    import time
    for file in Path('/data/new_merge_interface/app/fid_data').glob('*'):
        print(file)
        start_time1 = time.time()
        equipments = fid_parse_dxf(file, Path(file).name)
        print(time.time() - start_time1)
        start_time2 = time.time()
        for device in equipments:
            for e in equipments[device]:
                result = parse_block_attributes(e, Path(file).name)
                for r in result:
                    print(r)
        print('接口解析耗时', time.time() - start_time2,  time.time() - start_time1)
