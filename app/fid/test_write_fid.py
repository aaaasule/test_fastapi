from pathlib import Path
import time
from app.fid.fid_parser import fid_parse_dxf
import ezdxf


def replace_value_by_tag(block_ref, tag_str, new_value):
    """
    Helper function to replace text in an ATTRIB by its tag.
    """
    for attrib in getattr(block_ref, "attribs", []):
        if attrib.dxf.tag == tag_str:
            attrib.dxf.text = new_value
            return True
    return False

if __name__ == "__main__":


    # 打开你的 dxf 文件
    # doc = ezdxf.readfile("doc/YMTC^FID.PA^FAB1^F2.dxf")
    # msp = doc.modelspace()

    # # 目标 tag 和新值
    # target_handle = "18DBF2"
    # target_tag = "EQUIPMENT_CODE"
    # new_value = "B-002"

    # # 查找所有的块引用（INSERT 实体）
    # for insert in msp.query("INSERT"):
    #     if str(insert.dxf.handle) != target_handle:
    #         continue
        
    #     # 获取该 insert 下的所有属性；没有属性时为空列表
    #     for attrib in insert.attribs:
    #         if attrib.dxf.tag == target_tag:
    #             old_value = attrib.dxf.text  # 可记录旧值
    #             attrib.dxf.text = new_value
    #             print(f"块 {insert.dxf.name}({target_handle}) 中的 '{target_tag}' 已由 '{old_value}' 修改为 '{new_value}'")
    #             # break # 如果 tag 唯一，找到后可以跳出循环

    # # 保存修改后的文件（建议另存为新文件）
    # doc.saveas("doc/modified_drawing.dxf")

    for file in Path('doc/').glob('*'):
            print(file, type(file))
            if file.name != "YMTC^FID.PS^FAB1^F2.dxf":
                continue
            start_time1 = time.time()
            equipments = fid_parse_dxf(file, Path(file).name)
            print(time.time() - start_time1)
            start_time2 = time.time()
            for device in equipments:
                for e in equipments[device]:

                    if e.get('CAD_BLOCK_ID') == "18DBF2":
                    # if e.get('EQU.A') == "AKSCA01":
                        print(f"*******************")
                        print(e)
                        
                    # result = parse_block_attributes(e, Path(file).name)
                    # for r in result:
                    #     print(r)
            print('接口解析耗时', time.time() - start_time2,  time.time() - start_time1)
