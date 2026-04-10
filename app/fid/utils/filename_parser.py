import re
import os
import traceback
from pathlib import Path


def parse_filename(filename, fab_area):
    """
    解析 FID 和 ELD 文件名 (支持任意公司名前缀)
    规则：
    1. 公司名可以是任意字母/数字组合 (不再固定为 YMTC)
    2. 公司名后可跟数字表示区域 (如 Company2 -> Fab2)，无数字默认为 Fab1
    3. 后续格式保持不变：^TYPE.SYSTEM^BUILDING^FLOOR.ext 或 ^TYPE^BUILDING^FLOOR.ext
    """
    # 移除路径，只保留文件名
    base_name = os.path.basename(str(filename))

    # --- 修改点开始 ---
    # 原正则：r"^(YMTC)(\d*)"
    # 新正则：^([A-Za-z0-9_]+)(\d*)
    # 解释：
    # ([A-Za-z0-9_]+) : 捕获任意字母、数字、下划线作为公司名 (直到遇到数字或 ^)
    # (\d*)           : 捕获紧随其后的可选数字 (用于区分 Fab 编号)
    prefix_pattern = r"^([A-Za-z_]+)(\d*)"
    # --- 修改点结束 ---

    match = re.match(prefix_pattern, base_name)
    if not match:
        # 如果连公司名格式都不符合（例如以特殊字符开头），则解析失败
        print(f"前缀匹配失败：{base_name=}")
        return None

    company_prefix = match.group(1)
    area_num_str = match.group(2)

    # 确定 Fab 区域逻辑不变
    # 注意：这里假设没有数字就是 Fab1，有数字就是 Fab{数字}
    # 如果某些公司不需要 Fab 概念，可以在此处调整逻辑
    # if not area_num_str:
    #     fab_area = "Fab1"
    # else:
    #     fab_area = f"Fab{area_num_str}"

    # 去掉前缀部分，获取剩余字符串进行分割
    # 找到第一个 '^' 的位置
    first_caret_index = base_name.find('^')
    if first_caret_index == -1:
        # 如果没有分隔符，说明格式不对
        print(f"未找到分隔符 ^：{base_name=}")
        return None

    remaining_part = base_name[first_caret_index + 1:]
    parts = remaining_part.split('^')

    # 初始化结果字典
    result = {
        "original_filename": base_name,
        "company_name": company_prefix,  # 新增：记录原始公司名
        "fab_area": fab_area,
        "file_type": None,
        "system": None,
        "building": None,
        "floor": None,
        "extension": None
    }

    try:
        # 判断文件类型 (逻辑不变)
        if parts[0].startswith("FID"):
            # --- FID 格式解析 ---
            # 例子：FID.PE^WS^F4.dxf
            type_sys_raw = parts[0]

            # 防止没有 '.' 的情况报错
            if '.' not in type_sys_raw:
                return None

            file_type, system = type_sys_raw.split('.', 1)  # 使用 split('.', 1) 防止系统名里也有点

            building = parts[1]
            floor_raw = parts[2]

            floor_name, ext = os.path.splitext(floor_raw)

            floor_code = floor_name

            result.update({
                "file_type": file_type,
                "system": system,
                "building": building,
                "floor": floor_code,
                "extension": ext
            })

        elif parts[0] == "ELD":
            # --- ELD 格式解析 ---
            # 例子：ELD^ADB^F1B.dxf
            file_type = parts[0]
            building = parts[1]
            floor_raw = parts[2]

            floor_name, ext = os.path.splitext(floor_raw)

            floor_code = floor_name

            result.update({
                "file_type": file_type,
                "system": None,
                "building": building,
                "floor": floor_code,
                "extension": ext
            })
        else:
            # 既不是 FID 也不是 ELD
            print("既不是FID也不是ELD")
            return None

        return result

    except (IndexError, ValueError) as e:
        # print(f"解析失败：{base_name}, 错误原因：{e}")
        print(traceback.format_exc())
        return None


if __name__ == '__main__':

    folder = r'\\crosspub\pub\设备流体相关资料\厂商共享\【600】系统测试与数据迁移\【620】数据迁移\System\20260213\FID修正版for数据迁移'
    folder = r'\\crosspub\pub\设备流体相关资料\厂商共享\【600】系统测试与数据迁移'
    from pathlib import Path

    # === 测试用例 ===
    test_files = [
        "YMTC^FID.PE^WS^F4.dxf",
        "YMTC2^FID.HVAC^BLDG_A^F10.dxf",
        "YMTC^ELD^ADB^F1B.dxf",
        "YMTC3^ELD^CDC^F2C.dxf",
        "InvalidFile.txt"
    ]

    test_files = [str(filepath) for filepath in Path(folder).rglob('*.dxf')]


    print(f"{'原文件名':<35} | {'区域':<6} | {'类型':<4} | {'系统':<6} | {'楼栋':<8} | {'楼层'}")
    print("-" * 85)

    for f in test_files:
        data = parse_filename(f)
        #_, _, fab_area, file_type, system, building, floor, _ = list(data.values())
        #print(fab_area)
        if data:
            sys_val = data['system'] if data['system'] else "-"
            print(
                f"{data['original_filename']:<35} | {data['fab_area']:<6} | {data['file_type']:<4} | {sys_val:<6} | {data['building']:<8} | {data['floor']}")
        else:
            print(f"{Path(f).name:<35} | 解析失败")
