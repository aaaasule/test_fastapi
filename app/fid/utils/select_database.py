import pandas as pd
import psycopg2
from app.fid.utils.filename_parser import parse_filename
import warnings

from app.fid.utils.snake_to_camel import rename_list_dict_keys_to_camel

warnings.filterwarnings('ignore')


def get_db_config(fab_name):
    """根据 Fab 名称安全获取数据库配置"""
    fab_upper = str(fab_name).upper().strip()

    config_map = {
        'COMMON': {
            'host': '10.22.15.223', 'port': 5432,
            'user': 'efms', 'password': 'efms@1234', 'database': 'esidev2'
        },
        'FAB1': {
            'host': '10.22.15.223', 'port': 5432,
            'user': 'efms_fab1', 'password': 'Fab1_efms@1234', 'database': 'esidev2'
        },
        'FAB2': {
            'host': '10.22.15.223', 'port': 5432,
            'user': 'efms_fab2', 'password': 'Fab2_efms@1234', 'database': 'esidev2'
        },
        'FAB3': {
            'host': '10.22.15.223', 'port': 5432,
            'user': 'efms_fab3', 'password': 'Fab3_efms@1234', 'database': 'esidev2'
        }
    }

    #return config_map['FAB3']

    if fab_upper in config_map:
        print("链接-\n", config_map[fab_upper])
        return config_map[fab_upper]
    if fab_upper.startswith('FAB') and fab_upper[3:].isdigit():
        key = f"FAB{fab_upper[3:]}"
        if key in config_map:
            print("链接-\n", config_map[key])
            return config_map[key]

    raise ValueError(f"未知的 Fab 区域：'{fab_name}'")


def fetch_single_row(df, desc=""):
    """辅助函数：获取单行字典，若无数据返回 None"""
    if df.empty:
        print(f"⚠️ 未找到 {desc}")
        return None
    print(f"✅ 找到{desc}")
    return df.iloc[0].to_dict()


def fetch_all_rows(df, desc=""):
    """辅助函数：获取所有行为列表，若无数据返回空列表"""
    if df.empty:
        print(f"⚠️ 未找到 {desc} (返回空列表)")
        return []
    count = len(df)
    print(f"✅ 找到 {count} 条 {desc} 数据")
    return df.to_dict('records')


def select_data(filename, fab_area=None):
    conn = None
    try:
        print(f"[select_data] {filename=}")
        # 1. 解析文件名
        parsed = parse_filename(filename, fab_area)
        print(f"{parsed=}")
        company_name = parsed['company_name']
        if fab_area is None:
            fab_area = parsed['fab_area']
        system = parsed['system']  # 提取 system
        building_code = parsed['building']
        floor_code = parsed['floor']
        file_type = parsed['file_type']

        system_type = system if system else "-"
        print(f"📂 解析文件：{filename}")
        print(f"   -> Company: {company_name}, Fab: {fab_area}, System: {system_type}")
        print(
            f"{filename:<35} | {fab_area:<6} | {file_type:<4} | {system_type:<6} | {building_code:<8} | {floor_code}")
        # 2. 连接数据库
        db_config = get_db_config(fab_area)
        conn = psycopg2.connect(**db_config)
        print(f"🔗 已连接数据库用户：{db_config['user']}")

        # --- 3. 查询基础信息 (一对一) ---
        sql_building = f"""
            SELECT bd.*
            FROM efms_base_building bd 
            JOIN efms_base_company cd ON bd.company_id = cd.id  
            JOIN efms_base_fab fd ON bd.fab_id = fd.id
            WHERE fd.name = '{fab_area}' AND cd.name_en = '{company_name}' AND bd.code = '{building_code}'
        """
        print(f"sql_building--\n{sql_building}")
        df_building = pd.read_sql(sql_building, conn)
        building_info = fetch_single_row(df_building, "基础建筑信息")


        if not building_info:
            return {"status": "failed", "reason": "未找到匹配的建筑基础信息"}
        b_id = building_info['id']



        sql_company = f"""
            select * from efms_base_company cd where cd.name_en = '{company_name}'
            """
        print(f"sql_company--\n{sql_company}")
        df_company = pd.read_sql(sql_company, conn)
        company_info = fetch_single_row(df_company, f'公司信息({company_name})')
        c_id = company_info['id']


        sql_fab = f"""
        select * from efms_base_fab fd where fd.name = '{fab_area}'
        """
        print(f"{sql_fab=}")
        df_fab = pd.read_sql(sql_fab, conn)
        fab_info = fetch_single_row(df_fab, f'区域信息({fab_area})')
        f_id = fab_info['id']


        # --- 4. 查询楼层信息 (一对一) ---
        sql_level = f"SELECT * FROM efms_base_building_level WHERE building_id = {b_id} AND code = '{floor_code}'"
        print(f"{sql_level=}")
        df_level = pd.read_sql(sql_level, conn)
        level_info = fetch_single_row(df_level, f"楼层信息 ({floor_code})")


        if file_type == 'ELD':
            # --- 5. 查询集合信息 (一对多 -> List) ---

            # A. 设备列表 (Equipment List)
            sql_equip = f"""
                SELECT * FROM efms_eld_equipment 
                WHERE fab_id = {f_id} AND building_id = {b_id} AND building_level = '{floor_code}'
            """
            print(f"{sql_equip=}")
            df_equip = pd.read_sql(sql_equip, conn)
            print(df_equip.columns)
            equipment_list = fetch_all_rows(df_equip, "设备 (Equipment)")


            # B. 设备组列表 (Equipment Group List)
            sql_equip_grp = f"""
                SELECT * FROM efms_eld_equipment_group 
                WHERE fab_id = {f_id} AND building_id = {b_id}
            """
            print(f"{sql_equip_grp=}")
            df_equip_grp = pd.read_sql(sql_equip_grp, conn)
            #print(df_equip_grp.columns)
            equipment_group_list = fetch_all_rows(df_equip_grp, "设备组 (Equipment Group)")

            # C. 图层列表 (Layer List)
            sql_layer = f"""
                SELECT * FROM efms_base_layer 
                WHERE company_id = {c_id} AND fab_id = {f_id} AND building_id = {b_id}
            """
            print(f"{sql_layer=}")
            df_layer = pd.read_sql(sql_layer, conn)
            layer_list = fetch_all_rows(df_layer, "图层 (Layer)")

            # D. 网格列表 (Grid List)
            sql_grid = f"""
                SELECT * FROM efms_base_grid 
                WHERE company_id = {c_id} AND fab_id = {f_id} AND building_id = {b_id}
            """
            print(f"{sql_grid=}")
            df_grid = pd.read_sql(sql_grid, conn)
            grid_list = fetch_all_rows(df_grid, "网格 (Grid)")

            # --- 6. 构建最终结果 ---
            result = {
                "status": "success",
                "meta": {
                    "filename": filename,
                    "system": rename_list_dict_keys_to_camel(system),  # 从文件名带入 system
                    "fab_area": rename_list_dict_keys_to_camel(fab_area),
                    "company": rename_list_dict_keys_to_camel(company_name),
                    "building": rename_list_dict_keys_to_camel(building_code),
                    "building_level": rename_list_dict_keys_to_camel(floor_code),
                    "file_type": rename_list_dict_keys_to_camel(file_type)
                },
                "data": {
                    # 一对一对象 (Dict 或 None)
                    "company": rename_list_dict_keys_to_camel(company_info),
                    "fab": rename_list_dict_keys_to_camel(fab_info),
                    "building": rename_list_dict_keys_to_camel(building_info),
                    "buildingLevel": rename_list_dict_keys_to_camel(level_info),

                    # 一对多列表 (List of Dicts)
                    "equipmentList": rename_list_dict_keys_to_camel(equipment_list),
                    "equipmentGroupList": rename_list_dict_keys_to_camel(equipment_group_list),
                    "layerList": rename_list_dict_keys_to_camel(layer_list),
                    "gridList": rename_list_dict_keys_to_camel(grid_list)
                }
            }

            # 打印统计摘要
            print("\n📊 数据提取摘要:")
            print(f"   - Equipment Count: {len(equipment_list)}")
            print(f"   - EquipGroup Count: {len(equipment_group_list)}")
            print(f"   - Layer Count: {len(layer_list)}")
            print(f"   - Grid Count: {len(grid_list)}")

            return result

        else:
            sql_system = f"""
            select *, code as system_code from efms_sdc_systems where fab_id = '{f_id}' and code = '{system}'
            """
            print(f"{sql_system=}")
            df_system = pd.read_sql(sql_system, conn)
            system_dict = fetch_single_row(df_system, "系统System")
            s_id = system_dict['id']

            sql_subsystem = f"""
            select * from efms_sdc_subsystem where fab_id = '{f_id}' and system_id = '{s_id}'
            """
            print(f"{sql_subsystem=}")
            df_subsystem = pd.read_sql(sql_subsystem, conn)
            print(df_subsystem.columns)
            subsystem_list = fetch_all_rows(df_subsystem, "子系统信息")


            sql_field = f"""
            select * from efms_fid_fields where system_id = '{s_id}' and building_id = '{b_id}' and building_level = '{floor_code}'
            """
            print(f"{sql_field=}")
            df_field = pd.read_sql(sql_field, conn)
            print(df_field.columns)
            field_list = fetch_all_rows(df_field, "field信息")


            sql_interface = f"""
            select * from efms_fid_interfaces where building_id = '{b_id}' and building_level = '{floor_code}' 
            """
            print(f"{sql_interface=}")
            df_interface = pd.read_sql(sql_interface, conn)
            print(df_interface.columns)
            interface_list = fetch_all_rows(df_interface, "interface信息")


            sql_system_interface = f"""
            select * from efms_sdc_system_interface where fab_id = '{f_id}' and system_code = '{system_type}' 
            """
            print(f"{sql_system_interface=}")
            df_system_interface = pd.read_sql(sql_system_interface, conn)
            print(df_system_interface.columns)
            system_interface_list = fetch_all_rows(df_system_interface, "system_interface信息")


            print("\n📊 数据提取摘要:")
            print(f"   - Subsystem Count: {len(subsystem_list)}")
            print(f"   - Field Count: {len(field_list)}")
            print(f"   - Interface Count: {len(interface_list)}")
            print(f"   - SystemInterface Count: {len(system_interface_list)}")

            result = {
                "status": "success",
                "meta": {
                    "filename": filename,
                    "system": rename_list_dict_keys_to_camel(system),  # 从文件名带入 system
                    "fab_area": rename_list_dict_keys_to_camel(fab_area),
                    "company": rename_list_dict_keys_to_camel(company_name),
                    "building": rename_list_dict_keys_to_camel(building_code),
                    "building_level": rename_list_dict_keys_to_camel(floor_code),
                    "file_type": rename_list_dict_keys_to_camel(file_type)
                },
                "data": {
                    # 一对一对象 (Dict 或 None)
                    "company": rename_list_dict_keys_to_camel(company_info),
                    "fab": rename_list_dict_keys_to_camel(fab_info),
                    "building": rename_list_dict_keys_to_camel(building_info),
                    "buildingLevel": rename_list_dict_keys_to_camel(level_info),
                    "system": rename_list_dict_keys_to_camel(system_dict),
                    # 一对多列表 (List of Dicts)
                    "subsystemList": rename_list_dict_keys_to_camel(subsystem_list),
                    "fieldList": rename_list_dict_keys_to_camel(field_list),
                    "interfaceList": rename_list_dict_keys_to_camel(interface_list),
                    "systemInterfaceList": rename_list_dict_keys_to_camel(system_interface_list)
                }
            }
            return result
    except Exception as e:
        print(f"❌ 发生错误：{e}")
        import traceback
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}
    finally:
        if conn:
            conn.close()


# 测试调用
if __name__ == '__main__':
    # 测试用例
    res = select_data('YMTC2^ELD^FAB2^F4.dxf')

    # 简单验证返回结构
    if res and res.get('status') == 'success':
        data = res['data']
        print("\n--- 验证数据类型 ---")
        print(f"buildingLevel type: {type(data['buildingLevel'])}")  # 应为 dict 或 None
        print(f"equipmentList type: {type(data['equipmentList'])}")  # 应为 list
        print(f"layerList type: {type(data['layerList'])}")  # 应为 list

        # 示例：如果有设备，打印第一个设备的名字（假设有个 name 字段）
        if data['equipmentList']:
            print(f"First Equipment Keys: {list(data['equipmentList'][0].keys())}")
