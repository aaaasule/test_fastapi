# excel_parser.py
import datetime
import traceback
from typing import List
import pandas as pd
from models import Equipment, FileInfo


def parse_excel(excel_path, file_info: FileInfo = None, target_layers=None) -> List[Equipment]:
    """
    解析 Excel 文件，提取设备信息。

    文件格式要求：
    - 第10行是列名（header）
    - 第11行开始是数据
    - 列名：EquipmentCode, Equ.Group, Vendor, Vendor Description, Group/Process, 
            Building, B.Level, Grid_X, Grid_Y, Priority, Locked, Status, 
            Footprint [m2], M.front [mm], M.back [mm], M.left [mm], M.right [mm], 
            Weight [kg], weigt per m2 [kg], Vibration, Foundation

    筛选条件：Grid_X 和 Grid_Y 同时不为空（至少有一个坐标值的行）

    :param excel_path: Excel 文件路径
    :param file_info: 文件信息（用于绑定到 Equipment）
    :param target_layers: 目标层筛选（Excel解析中暂不使用，保持接口一致性）
    :return: Equipment 列表
    """
    start_time = datetime.datetime.now()

    try:
        print(f"{excel_path=} {type(excel_path)}")

        # 读取Excel，第10行作为header（pandas的header是0-indexed，所以是9）
        # skiprows=9 表示跳过前9行，从第10行开始读取
        df = pd.read_excel(
            excel_path,
            header=9,  # 第10行作为列名（0-indexed）
            engine='openpyxl',
            sheet_name='Report'
        )

        print(f"原始数据行数: {len(df)}")
        print(f"列名: {list(df.columns)}")

    except Exception as e:
        print(traceback.format_exc())
        raise Exception(f'Excel解析失败: {str(e)}')

    equipments: List[Equipment] = []

    # 标准化列名（去除空格，处理可能的换行符等）
    #df.columns = [str(col).strip().replace('\n', ' ') for col in df.columns]
    df.columns = [str(col) for col in df.columns]
    print(f"{df.columns=}")
    # 筛选 Grid_X 和 Grid_Y 同时不为空的行
    # 使用 notna() 和 非空字符串判断，确保数值和字符串类型都能处理
    df['Grid_X'] = df['Grid_X'].astype(str).str.strip()
    df['Grid_Y'] = df['Grid_Y'].astype(str).str.strip()

    # 筛选条件：Grid_X 和 Grid_Y 都不为空，且不是 'nan' 字符串
    if target_layers is not None:
        mask = (
                (df['Grid_X'].notna()) &
                (df['Grid_Y'].notna()) &
                (df['Priority'].str.isin(target_layers))
        )
    else:
        mask = (
                (df['Grid_X'].notna()) &
                (df['Grid_Y'].notna())
        )

    df_filtered = df[mask].copy()
    print(f"筛选后数据行数（Grid_X和Grid_Y同时不为空）: {len(df_filtered)}")

    # 遍历数据行创建设备对象
    for idx, row in df_filtered.iterrows():
        try:

            grid_x = row['Grid_X']

            grid_y = row['Grid_Y']


            # 处理 EquipmentCode（对应 DXF 中的 TOOL_ID）
            tool_id = str(row['EquipmentCode']).strip() if pd.notna(row['EquipmentCode']) else ''
            # 删除开头的 ^（如果有）
            tool_id = tool_id[1:].strip() if tool_id.startswith('^') else tool_id

            # 获取 Owner（Equ.Group 列，对应 DXF 中的 OWNER 或 EQU.GROUP）
            owner_code = str(row['Equ.Group']).strip().upper() if pd.notna(row['Equ.Group']) else ''

            # 从 file_info 获取 group_id
            group_id = file_info.owner2id.get(owner_code) if file_info is not None and owner_code != '' else None

            # 获取 Building 和 Level 信息
            building = str(row['Building']).strip() if pd.notna(row['Building']) else ''
            b_level = str(row['B.Level']).strip() if pd.notna(row['B.Level']) else ''

            # 构建 Equipment 对象
            # 注意：Excel中没有CAD特有的属性（如cad_block_name, layer, angle等），这些字段留空或给默认值
            eq = Equipment(
                id=file_info.id_ if file_info is not None else None,
                fab_id=file_info.fab_id if file_info is not None else None,
                building_id=file_info.building_id if file_info is not None else None,
                building_level=file_info.building_level if file_info is not None else None,
                group_id=group_id,
                tool_id=tool_id if tool_id else None,
                owner=owner_code if owner_code else None,
                vendor=str(row['Vendor']).strip() if pd.notna(row['Vendor']) else None,
                model=str(row['Vendor Description']).strip() if pd.notna(row['Vendor Description']) else None,
                # Excel中没有直接的 BAY_LOCATION，可以用 Building + B.Level 组合
                bay_location=None,
                record=None,  # Excel中没有对应字段，或可以映射其他列

                # CAD固有属性（Excel中无对应数据，给默认值或None）
                cad_block_name=None,  # Excel中没有块名
                layer=str(row['Priority']),  # Excel中没有图层
                angle=0.0,  # 无旋转角度
                true_color=0,  # 无颜色信息
                insert_point_x=0.,  # 使用 Grid_X 作为插入点X
                insert_point_y=0.,  # 使用 Grid_Y 作为插入点Y
                insert_point_z=0.,  # 假设Z为0
                center_point_x=0.,  # 中心点与插入点相同
                center_point_y=0.,

                cad_block_id=None,  # Excel中没有句柄
                file_info=file_info,

                # Excel特有的额外字段（如果Equipment模型支持扩展，可以添加）
                # 如果需要存储额外信息，可以放在record中或使用动态属性
            )

            # 调试输出
            if eq.group_id is None:
                print(f"file_info is None -> {file_info is None}")
                print(f"{owner_code=}")
                print(f"{file_info is not None} {owner_code != ''} {file_info is not None and owner_code != ''}")
            equipments.append(eq)

        except Exception as e:
            print(f"处理第 {idx + 11} 行数据时出错: {str(e)}")
            print(traceback.format_exc())
            continue

    print(f"共解析出 {len(equipments)} 个设备")
    print(f"解析文件耗时： {datetime.datetime.now() - start_time}")
    return equipments


def parse_equipment_excel(excel_path, file_info: FileInfo = None) -> List[Equipment]:
    """
    简化版函数，专门用于解析设备Excel文件。
    与parse_excel功能相同，只是更明确的命名。
    """
    return parse_excel(excel_path, file_info)


if __name__ == '__main__':

    file_path = '/data/new_merge_interface/app/fid/temp_uploads/Fab2 Equipment20260202.xlsx'
    from pathlib import Path
    file_info = {
        "filename": Path(file_path).name,
        "company": 1,
        "building_id": 1,
        "building_level": "F3",
        "fab_id": 1,
        "id_": 1,
        "owner2id": {
            "AE": 1,
            "BEOP": 4,
            "BOND": 5,
            "CHEMICAL LAB": 6,
            "CMP": 7,
            "CMS": 8,
            "DIFF": 10,
            "DM": 11,
            "ECD": 12,
            "EPI": 13,
            "ESH": 14,
            "FA LAB": 16,
            "FAC": 17,
            "GMS": 18,
            "HK": 19,
            "HOOD": 20,
            "IMP": 21,
            "LEAK SENSOR": 22,
            "LITHO": 23,
            "MAIN-TOOL HDC": 24,
            "MF": 25,
            "MI": 26,
            "OS": 27,
            "PACKAGE LAB": 28,
            "PCL": 29,
            "PETE LAB": 30,
            "PLC": 31,
            "PSH": 32,
            "PVD": 33,
            "QE": 34,
            "RCM": 35,
            "SHK.TYP": 37,
            "SOCKET PANEL": 38,
            "AMHS": 3,
            "ETCH": 15,
            "AL LAB": 2,
            "CVD": 9,
            "SUB-TOOL HDC": 39,
            "TESTING": 40,
            "UNIMOS": 41,
            "WAFER SORT": 42,
            "WAT": 43,
            "WET": 44,
            "YAE": 45,
            "YAE LAB": 46,
            "YE": 47,
            "YMTS": 48,
            "ASD": 93,
            "QWQW": 96,
            "AMHS2": 97,
            "SADCAS": 99,
            "2222": 87,
            "123123": 132,
            "12123": 138,
            "DEVICE": 140,
            "TEST": 133,
            "ES PANEL": 141,
            "IT": 142,
            "NONE": 143,
            "RE LAB": 144,
            "GAS": 145,
            "OTHER": 146,
            "POWER BOX": 147,
            "OPC": 148,
            "RAW MATERIAL": 155,
            "SKC": 157,
            "TEST&.": 161,
            "123": 158
        }
    }
    file_info = FileInfo(
            filename=file_info['filename'],
            company=file_info['company'],
            building_id=file_info['building_id'],
            building_level=file_info['building_level'],
            fab_id=file_info['fab_id'],
            id_=file_info['id_'],
            owner2id=file_info['owner2id']
        )

    result = parse_excel(file_path, file_info)
    print(f"{result=}")
