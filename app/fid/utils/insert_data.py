import pandas as pd
import psycopg2
from app.fid.utils.filename_parser import parse_filename
import warnings

from app.fid.utils.snake_to_camel import rename_list_dict_keys_to_camel

warnings.filterwarnings('ignore')

import datetime
import traceback

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

    if fab_upper in config_map:
        return config_map[fab_upper]
    if fab_upper.startswith('FAB') and fab_upper[3:].isdigit():
        key = f"FAB{fab_upper[3:]}"
        if key in config_map:
            return config_map[key]

    raise ValueError(f"未知的 Fab 区域：'{fab_name}'")


def insert_data(check_result, fab_area):
    conn = None
    cursor = None
    try:
        filename = check_result['file']
        parsed = parse_filename(filename, fab_area)

        file_type = parsed['file_type']

        db_config = get_db_config(fab_area)
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        print(f"🔗 已连接数据库用户：{db_config['user']}")

        if file_type == 'FID':

            field_id_cache = {}
            # 定义 SQL 模板 (使用 %s 作为占位符)
            # 注意：列名不要加引号（除非有大写字母），值的位置用 %s
            sql_field = """
                INSERT INTO efms_fid_fields (
                    id, subsystem_id, building_id, building_level, code,
                    uni_code, distribution_box, pos_max_flow, 
                    status, locked, create_time,
                    last_modify_time, archive, cad_block_name,
                    cad_block_id, layer, insert_point_x, insert_point_y,
                    insert_point_z, angle, true_color, vmb_type, system_id, unit,
                    chemical_name, creator_id
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s
                )
            """

            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for field_data in check_result['data']['field']:

                cursor.execute("SELECT nextval('efms_fid_fields_seq')")
                new_id = cursor.fetchone()[0]
                print(f"预分配的 ID 是：{new_id}")

                field_id_cache[field_data.get('uniCode')] = new_id
                # 准备数据元组，顺序必须与 SQL 中的 %s 一一对应
                # 处理可能为 None 的值，psycopg2 会自动将 Python 的 None 转为 SQL 的 NULL
                values = (
                    new_id,
                    field_data.get('subsystem_id'),  # 1
                    field_data.get('building_id'),  # 2
                    field_data.get('building_level'),  # 3
                    field_data.get('code'),  # 4
                    field_data.get('uniCode'),  # 5
                    field_data.get('distributionBox'),  # 6
                    field_data.get('maxDesignFlow'),  # 7
                    field_data.get('operation'),  # 8
                    field_data.get('locked'),  # 9
                    now_str,  # 10
                    now_str,  # 11
                    0,  # 12
                    field_data.get('cadBlockName'),  # 13
                    field_data.get('cadBlockId'),  # 14
                    field_data.get('layer'),  # 15
                    field_data.get('insertPointX'),  # 16
                    field_data.get('insertPointY'),  # 17
                    field_data.get('insertPointZ'),  # 18
                    field_data.get('angle'),  # 19
                    field_data.get('trueColor'),  # 20
                    field_data.get('vmb_type'),  # 21
                    field_data.get('system_id'),  # 22
                    field_data.get('unit'),
                    field_data.get('chemical_name'),
                    'E908112'
                )

                # 执行插入
                try:
                    cursor.execute(sql_field, values)
                except Exception as sql_e:
                    # ✅ 使用 mogrify 输出实际执行的 SQL
                    executed_sql = cursor.mogrify(sql_field, values)
                    print(f"执行的SQL: {executed_sql.decode('utf-8')}")
                    print()

                    print(traceback.format_exc())
                    raise Exception(str(sql_e))

            # 提交事务
            conn.commit()
            print(f"✅ 成功插入 {len(check_result['data']['field'])} 条field记录")

            sql_interface = """
                INSERT INTO efms_fid_interfaces (
                    id, field_id, building_id, building_level, code,
                    uni_code, distribution_box, max_design_flow, 
                    status, locked, create_time,
                    last_modify_time, archive, cad_block_name,
                    cad_block_id, layer, insert_point_x, insert_point_y,
                    insert_point_z, angle, true_color,  unit, con_size, con_type, 
                    creator_id
                ) VALUES (
                    nextval('efms_fid_interface_seq'), %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s
                )
            """

            for interface_data in check_result['data']['interfaces']:
                field_code = interface_data['field_code']
                if field_code not in field_id_cache:
                    df_field = pd.read_sql(
                        f"""select * from efms_fid_fields where uni_code = '{field_code}'""", conn
                    )
                    if not df_field.empty:
                        field_id = int(df_field.iloc[0]['id'])
                    else:
                        raise Exception('没有field_id')
                else:
                    field_id = field_id_cache[field_code]

                values = (
                    field_id,  # 1
                    interface_data.get('building_id'),  # 2
                    interface_data.get('building_level'),  # 3
                    interface_data.get('code'),  # 4
                    interface_data.get('uniCode'),  # 5
                    interface_data.get('distributionBox'),  # 6
                    interface_data.get('maxDesignFlow'),  # 7
                    interface_data.get('operation'),  # 8
                    interface_data.get('locked'),  # 9
                    now_str,  # 10
                    now_str,  # 11
                    0,  # 12
                    interface_data.get('cadBlockName'),  # 13
                    interface_data.get('cadBlockId'),  # 14
                    interface_data.get('layer'),  # 15
                    interface_data.get('insertPointX'),  # 16
                    interface_data.get('insertPointY'),  # 17
                    interface_data.get('insertPointZ'),  # 18
                    interface_data.get('angle'),  # 19
                    interface_data.get('trueColor'),  # 20
                    interface_data.get('unit'),  # 21
                    interface_data.get('conSize'),  # 22
                    interface_data.get('conType'),
                    'E908112'
                )

                # 执行插入
                try:
                    cursor.execute(sql_interface, values)
                except Exception as sql_e:
                    # ✅ 使用 mogrify 输出实际执行的 SQL
                    executed_sql = cursor.mogrify(sql_interface, values)
                    print(f"执行的SQL: {executed_sql.decode('utf-8')}")
                    print()

                    print(traceback.format_exc())
                    raise Exception(str(sql_e))

            conn.commit()
            print(f"✅ 成功插入 {len(check_result['data']['interfaces'])} 条interface记录")
        else: #ELD

            tool_id_cache = {}
            # 定义 SQL 模板 (使用 %s 作为占位符)
            # 注意：列名不要加引号（除非有大写字母），值的位置用 %s
            sql_equip = """
                INSERT INTO efms_eld_equipment (
                    id, fab_id, building_id, 
                    building_level, code, vendor, 
                    model, process, grid_x, 
                    grid_y, layer, locked, 
                    status, create_time, last_modify_time, 
                    bay_location, record, cad_block_name, 
                    cad_block_id, insert_point_x, insert_point_y, 
                    insert_point_z, angle, true_color,
                    creator_id, group_id, archive
                ) VALUES (
                    %s, %s, %s, 
                    %s, %s, %s, 
                    %s, %s, %s,
                    %s, %s, %s, 
                    %s, %s, %s,
                    %s, %s, %s, 
                    %s, %s, %s, 
                    %s, %s, %s,
                    %s, %s, %s
                )
            """

            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for equip_data in check_result['data']:

                cursor.execute("SELECT nextval('efms_fid_fields_seq')")
                new_id = cursor.fetchone()[0]
                print(f"预分配的 ID 是：{new_id}")
                # tool_id = equip_data.get('code')
                # if tool_id not in tool_id_cache:
                #     tool_id_cache[tool_id] = new_id

                values = (
                    new_id,
                    equip_data['fabId'],
                    equip_data['buildingId'],
                    equip_data['buildingLevel'],
                    equip_data['code'],
                    equip_data['vendor'],
                    equip_data['model'],
                    equip_data['process'],
                    equip_data['gridX'],
                    equip_data['gridY'],
                    equip_data['layer'],
                    0,
                    'add',
                    now_str,
                    now_str,
                    equip_data['bayLocation'],
                    equip_data['record'],
                    equip_data['cadBlockName'],
                    equip_data['cadBlockId'],
                    equip_data['insertPointX'],
                    equip_data['insertPointY'],
                    equip_data['insertPointZ'],
                    equip_data['angle'],
                    equip_data['trueColor'],
                    'E908112',
                    equip_data['groupId'],
                    0
                )

                # 执行插入
                try:
                    cursor.execute(sql_equip, values)
                except Exception as sql_e:
                    # ✅ 使用 mogrify 输出实际执行的 SQL
                    executed_sql = cursor.mogrify(sql_equip, values)
                    print(f"执行的SQL: {executed_sql.decode('utf-8')}")
                    print()

                    print(traceback.format_exc())
                    raise Exception(str(sql_e))

            conn.commit()
            print(f"✅ 成功插入 {len(check_result['data'])} 条interface记录")

    except Exception as e:
        # if conn:
        #     conn.rollback()  # 出错回滚
        print(f"❌ 发生错误：{e}")
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
