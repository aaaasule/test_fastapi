# /app/fid/api_util.py
import json
import os
import sys
from pathlib import Path

# 获取当前文件绝对路径：/data/new_merge_interface/app/fid/api_util.py
current_file = Path(__file__).resolve()
root_dir = current_file.parent.parent.parent  # 向上两级得到 project 根目录
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from typing import List
from dataclasses import asdict

from app.fid.schemas import CheckError, EquipmentItem
from app.fid.models import Equipment, FileInfo, CheckResult
from app.fid.dxf_parser import parse_dxf
from app.fid.fid_parser import fid_parse_dxf
# from excel_parser import parse_excel

from app.fid.validators import (
    DXFFilenameValidator,
    ELDRuleValidator,
    ELDChangeValidator,
    DEFAULT_FILENAME_RULES,
    DEFAULT_RULE_RULES,
    DEFAULT_CHANGE_RULES,
    GridPillarFinder,
    GridPillarMatchRule,
    GridSearcher,

    FIDRuleValidator,
    FIDDeleteValidator,
    DEFAULT_FID_RULE_RULES,
    FID_DELETE_RULES,

    EXCEL_CHANGE_RULES,
    DEFAULT_EXCEL_RULES

)

from app.fid.utils.snake_to_camel import snake_to_camel
from app.fid.utils.parse_block_attributes import parse_block_attributes
from app.fid.utils.parse_search_id import parse_search_id
from app.fid.utils.process_fid_request import convert_dict_keys_to_snake
from app.fid.utils.replace_nan_with_none import replace_nan_with_none
from app.fid.utils.check_result_is_valid import check_result_valid
from app.fid.utils import safe_json_loads

import traceback
import pandas as pd

pd.set_option('display.max_rows', None)

# 导入 FTP 和数据库相关工具
from app.config import fid_config as config
#from app.config.fid_config import FTP_CONFIG

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


async def _eld_check(
        file_path,
        company,
        fab,
        building,
        buildingLevel,
        equipmentList,  # 必须是字符串
        equipmentGroupList,
        layerList,
        gridList,
        cache_folder,
        mission_start_time,
        mode
):
    try:
        filename = Path(file_path).name
        is_excel = filename.endswith('.xlsx')

        company = safe_json_loads(company)
        fab = safe_json_loads(fab)
        building = safe_json_loads(building)
        building_level = safe_json_loads(buildingLevel)
        equipment_list = safe_json_loads(equipmentList)
        equipment_group_list = safe_json_loads(equipmentGroupList)
        layer_list = safe_json_loads(layerList)
        grid_list = safe_json_loads(gridList) if not is_excel else {}

        request_data = {
            'company': company,
            'fab': fab,
            'building': building,
            'building_level': building_level,
            'equipment_list': [el for el in equipment_list if not str(el['status']).startswith('not')],
            'delete_equipment_list': [el for el in equipment_list if str(el['status']).startswith('not')],
            'equipment_group_list': equipment_group_list,
            'layer_list': layer_list,
            'grid_list': grid_list
        }

        # 过滤逻辑
        equipment_group_list = [egl for egl in equipment_group_list if
                                egl.get('buildingId') == building_level.get('buildingId')]

        company_id = company['id']
        fab_id = fab['id']
        building_id = building['id']
        building_level_code = building_level['code']

        all_results = []  # 收集所有 CheckResult
        current_equipment_list = []

        # 1. 设置全局约束
        TARGET_LAYERS = layer_list
        EQUIPMENT_GROUPS = equipment_group_list
        GRID_INFO = {
            'Field': [gi['field'] for gi in grid_list],
            'XY': [gi['axis'] for gi in grid_list],
            'Value_From': [gi['valueFrom'] for gi in grid_list],
            'Value_To': [gi['valueTo'] for gi in grid_list],
        }

        checker_info = {
            'layer_list': TARGET_LAYERS,
            'equipment_group_list': EQUIPMENT_GROUPS,
            'grid_info': GRID_INFO
        }

        owner2id_map = {}
        for d in EQUIPMENT_GROUPS:
            owner_code_upper = d['code'].upper()
            if owner_code_upper not in owner2id_map:
                owner2id_map[owner_code_upper] = d['id']

        file_info = FileInfo(
            filename=os.path.basename(file_path),
            company=company_id,
            building_id=building_id,
            building_level=building_level_code,
            fab_id=fab_id,
            id_=company_id,
            owner2id=owner2id_map
        )

        # 2. 文件名校验
        filename_validator = DXFFilenameValidator(DEFAULT_FILENAME_RULES)
        params = {'company': company_id,
                  'building': building_id,
                  'level': building_level_code}
        fname_errors = filename_validator.validate(file_path, **params)
        all_results.extend(fname_errors)

        # 3. 尝试解析 DXF
        if not os.path.exists(file_path):
            raise ValueError(f"DXF 文件不存在：{file_path}")

        try:
            current_equipment_list = parse_dxf(file_path, file_info=file_info, target_layers=TARGET_LAYERS)
            cache_dxf_result = [asdict(cel) for cel in current_equipment_list]
            with open(Path(cache_folder) / f"parser_{mission_start_time}.json", 'w', encoding='utf-8',
                      errors='replace') as f:
                f.write(json.dumps(cache_dxf_result, ensure_ascii=False, indent=2))
        except Exception as dxf_exception:
            raise Exception(f'dxf 文件解析遇到错误：{str(dxf_exception)}')

        # 4. 规范校验
        if current_equipment_list:
            rule_validator = ELDRuleValidator(DEFAULT_RULE_RULES if not is_excel else DEFAULT_EXCEL_RULES)
            rule_results = rule_validator.validate(current_equipment_list, checker_info, request_data)
            all_results.extend(rule_results)

        # 柱网匹配从规范校验分离
        if len(grid_list) > 0:
            grid_pillar_finder = GridPillarFinder(
                field=GRID_INFO['Field'],
                XY=GRID_INFO['XY'],
                value_from=GRID_INFO['Value_From'],
                value_to=GRID_INFO['Value_To']
            )

            grid_searcher = GridSearcher([GridPillarMatchRule(
                grid_pillar_finder=grid_pillar_finder
            )])
            rule_results = grid_searcher.validate(current_equipment_list, checker_info)
            all_results.extend(rule_results)

        # 5. 变更校验
        previous_equips = {
            'fab': [],
            'building_level': []
        }
        virtual_status_dict = {}
        for item in equipment_list:
            prev_eq = Equipment(
                id=item.get('id'),
                fab_id=item.get('fabId'),
                building_id=item.get('buildingId'),
                building_level=item.get('buildingLevel'),
                group_id=item.get('groupId'),
                tool_id=item['code'],
                vendor=item.get('vendor'),
                model=item.get('model'),
                process=item.get('process'),
                is_virtual_eqp=item.get('isVirtualEqp'),
                grid_x=item.get('gridX'),
                grid_y=item.get('gridY'),
                locked=item.get('locked'),
                bay_location=item.get('bayLocation'),
                record=item.get('record'),
                cad_block_name=item.get('cadBlockName'),
                layer=item.get('layer'),
                angle=item.get('angle'),
                true_color=item.get('trueColor'),
                insert_point_x=round(float(item.get('insertPointX', .0) or .0), 4),
                insert_point_y=round(float(item.get('insertPointY', .0) or .0), 4),
                insert_point_z=round(float(item.get('insertPointZ', .0) or .0), 4),
                center_point_x=round(float(item.get('centerPointX', .0) or .0), 4),
                center_point_y=round(float(item.get('centerPointY', .0) or .0), 4),
                cad_block_id=item.get('cadBlockId')
            )
            if int(item.get('fabId')) == int(fab.get('id')):
                previous_equips['fab'].append(prev_eq)
            if (item.get('buildingId') == building_level.get('buildingId')) and \
                    (item.get('buildingLevel') == building_level.get('code')):
                previous_equips['building_level'].append(prev_eq)

        # 变更校验
        if current_equipment_list:
            change_validator = ELDChangeValidator(DEFAULT_CHANGE_RULES if not is_excel else EXCEL_CHANGE_RULES)
            change_results = change_validator.validate(current_equipment_list, previous_equips, request_data)
            all_results.extend(change_results)

        # 6. 分离 error / warning
        errors_results = [r for r in all_results if r.type == "error"]
        warnings_results = [r for r in all_results if r.type == "warning"]

        # 9. 转换当前设备为响应格式
        data = []
        full_equipment_list = current_equipment_list

        curr_map = {eq.tool_id: eq for eq in current_equipment_list}
        for prev_eq in previous_equips['building_level']:
            if prev_eq.tool_id not in curr_map:
                eq_dict = asdict(prev_eq)
                eq_dict["operation"] = "delete"
                deleted_eq = Equipment(**eq_dict)
                full_equipment_list.append(deleted_eq)

        equipment_error_map = {}
        id_map = {}
        current_description = {}
        for eq in current_equipment_list:
            equipment_error_map[f"{eq.tool_id}-{eq.cad_block_id}"] = []
            id_map[eq.cad_block_id] = eq.tool_id
            current_description[f"{eq.tool_id}-{eq.cad_block_id}"] = []

        for result in all_results:
            if result.equipment == None:
                continue

            cad_block_id = result.equipment.cad_block_id
            if f"{result.equipment.tool_id}-{cad_block_id}" in equipment_error_map:
                if result.type != 'warning':
                    if result.description not in current_description[f"{result.equipment.tool_id}-{cad_block_id}"]:
                        equipment_error_map[f"{result.equipment.tool_id}-{cad_block_id}"].append({
                            "errorName": result.name,
                            "errorType": result.type,
                            "errorDescription": result.description
                        })
                        current_description[f"{result.equipment.tool_id}-{cad_block_id}"].append(result.description)

        final_error_results = []
        error_seen = set()

        for eq in current_equipment_list:
            _search_id = f"{eq.tool_id}-{eq.cad_block_id}"
            if _search_id in equipment_error_map and len(equipment_error_map[_search_id]) > 0:
                eq.errors = equipment_error_map[_search_id]
                _result = asdict(eq)
                _result['code'] = _result.pop('tool_id')
                if _search_id not in error_seen:
                    final_error_results.append(_result)
                    error_seen.add(_search_id)

        equipment_pd = pd.DataFrame.from_dict(equipment_list)

        final_warning_results = []
        warning_seen = set()

        for warning_data in warnings_results:
            eq = warning_data.equipment
            _result = asdict(eq)

            eq_id = None
            if not equipment_pd.empty:
                eq_id_pd = equipment_pd[equipment_pd['code'] == _result['tool_id']]
                if not eq_id_pd.empty:
                    eq_id = int(eq_id_pd.iloc[0]['id'])

            _result['code'] = _result.pop('tool_id')
            _result['id'] = eq_id
            _result['fab_id'] = fab_id
            _result['building_id'] = building_id
            _result['building_level'] = building_level_code
            _result['description'] = warning_data.description
            if f"{_result['code']}_{_result['cad_block_id']}" not in warning_seen:
                warning_seen.add(f"{_result['code']}_{_result['cad_block_id']}")
                final_warning_results.append(_result)

        if len(final_error_results) != 0:
            return_result = {
                'code': 200,
                'message': "调用成功",
                'success': False,
                'data': [
                    {snake_to_camel(k): v for k, v in d.items() if k in EquipmentItem.model_fields and k != 'operation'}
                    for d in final_error_results
                ]
            }
            return return_result
        elif len(final_warning_results) != 0:
            return_result = {
                'code': 200,
                'message': "调用成功",
                'success': True,
                'data': [
                    {snake_to_camel(k): v for k, v in d.items() if k in EquipmentItem.model_fields and k != 'errors'}
                    for d in final_warning_results
                ]
            }
            return return_result
        else:
            return_result = {
                'code': 200,
                'message': "调用成功",
                'success': True,
                'data': []
            }
            return return_result

    except Exception as e:
        return_result = {
            "code": 400,
            "message": f"算法调用失败：{str(e)}",
            "traceback": traceback.format_exc(),
        }
        return return_result


def convert_to_check_errors(results: List[CheckResult]) -> List[CheckError]:
    from collections import defaultdict
    grouped = defaultdict(list)
    for r in results:
        key = (r.name, r.type, r.description)
        grouped[key].append(r.detail)  # ← 直接 append 原始 detail 字典

    return [
        CheckError(
            name=name,
            type=type_,
            description=desc,
            items=details
        )
        for (name, type_, desc), details in grouped.items()
    ]


async def _fid_check(
        file_path,
        company,
        fab,
        building,
        buildingLevel,
        system,  # 必须是字符串
        subsystemList,
        fieldList,
        interfaceList,
        systemInterfaceList,
        cache_folder,
        mission_start_time,
        mode
):
    try:
        company = safe_json_loads(company)
        fab = safe_json_loads(fab)
        building = safe_json_loads(building)
        building_level = safe_json_loads(buildingLevel)
        system = safe_json_loads(system)
        subsystem_list = safe_json_loads(subsystemList)
        field_list = safe_json_loads(fieldList)
        interface_list = safe_json_loads(interfaceList)
        system_interface_list = safe_json_loads(systemInterfaceList)

        filename = Path(file_path).name

        company = {'id': company['id'], 'name': company['nameEn']}
        fab = {'id': fab['id'], 'name': fab['name']}
        building = {'id': building['id'], 'name': building['name']}
        building_level = {'id': building_level['id'], 'name': building_level['name']}
        system = {'id': system['id'], 'name': system['code']}

        # 列表转换
        subsystem_list = [convert_dict_keys_to_snake(sl) for sl in subsystem_list]

        active_field_list = []
        delete_field_list = []
        for fl in field_list:
            if fl['status'] != 'not_existing_in_fid':
                active_field_list.append(convert_dict_keys_to_snake(fl))
            else:
                delete_field_list.append(convert_dict_keys_to_snake(fl))

        active_interface_list = []
        delete_interface_list = []
        for il in interface_list:
            if il['status'] != 'not_existing_in_fid':
                active_interface_list.append(convert_dict_keys_to_snake(il))
            else:
                delete_interface_list.append(convert_dict_keys_to_snake(il))

        field_list = [convert_dict_keys_to_snake(fl) for fl in field_list]
        interface_list = [convert_dict_keys_to_snake(il) for il in interface_list]
        system_interface_list = [convert_dict_keys_to_snake(sil) for sil in system_interface_list]

        # --- 阶段 2: DataFrame 构建 ---
        field_pd = pd.DataFrame.from_dict(field_list).add_prefix('FIELD.')
        subsystem_pd = pd.DataFrame.from_dict(subsystem_list).add_prefix('SUBSYSTEM.')
        interface_pd = pd.DataFrame.from_dict(interface_list).add_prefix('INTERFACE.')

        if interface_pd.empty:
            interface_pd = pd.DataFrame([],
                                        columns=['id', 'field_id', 'uni_code', 'cad_block_id', 'status']).add_prefix(
                'INTERFACE.')

        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
                                                 'code', 'uni_code', 'cad_block_id',
                                                 'insert_point_x', 'insert_point_y',
                                                 'insert_point_z', 'status']).add_prefix('FIELD.')

        if subsystem_pd.empty:
            subsystem_pd = pd.DataFrame([], columns=['id', 'system_id', 'code', 'is_slurry']).add_prefix('SUBSYSTEM.')

        delete_field_set = set([dfl['uni_code'] for dfl in delete_field_list])
        delete_interface_set = set([dil['uni_code'] for dil in delete_interface_list])

        request_data = {
            'building': building,
            'building_level': building_level,
            'subsystem_list': subsystem_list,
            'field_list': active_field_list,
            'interface_list': active_interface_list,
            'delete_field_set': delete_field_set,
            'delete_interface_set': delete_interface_set,
            'system_interface_list': system_interface_list,
            'system': system,
            'filename': filename,
            'fab': fab,

            'disable_fab': config.DISABLED_FAB_TUPLE
        }

        field_and_subsystem_pd = pd.merge(
            field_pd,
            subsystem_pd,
            left_on='FIELD.subsystem_id',
            right_on='SUBSYSTEM.id',
            how='left'
        )
        interface_and_subsystem_pd = pd.merge(
            interface_pd,
            field_and_subsystem_pd,
            left_on='INTERFACE.field_id',
            right_on='FIELD.id',
            how='left'
        )

        # --- 阶段 3: DXF 解析 ---
        if not os.path.exists(file_path):
            raise ValueError(f"DXF 文件不存在：{file_path}")

        try:
            current_equipment_list = fid_parse_dxf(file_path, filename=filename)
            with open(Path(cache_folder) / f"parser_{mission_start_time}.json", 'w', encoding='utf-8',
                      errors='replace') as f:
                f.write(json.dumps(current_equipment_list, ensure_ascii=False, indent=2))
        except Exception as dxf_exception:
            raise Exception(f'dxf 文件解析遇到错误：{str(dxf_exception)}')

        # --- 阶段 4: 规则校验 ---
        all_results = []

        if current_equipment_list:
            rule_validator = FIDRuleValidator(DEFAULT_FID_RULE_RULES)
            rule_results = rule_validator.validate(current_equipment_list, request_data)
            all_results.extend(rule_results)

            rule_validator_del = FIDDeleteValidator(FID_DELETE_RULES)
            rule_results_del = rule_validator_del.validate(current_equipment_list, request_data)
            all_results.extend(rule_results_del)

        # --- 阶段 5: 结果分离与初步处理 ---
        errors_results = [r for r in all_results if r.type == "error"]
        warnings_results = [r for r in all_results if r.type == "warning"]

        full_equipment_list = current_equipment_list
        equipment_error_map = {}

        # 初始化 map
        for result in all_results:
            if not result.equipment or len(result.equipment) == 0:
                continue
            eq = result.equipment[0]
            _id = eq.get("CAD_BLOCK_ID")
            if _id not in equipment_error_map:
                equipment_error_map[_id] = []

        # 填充 map
        for result in all_results:
            if not result.equipment or len(result.equipment) == 0:
                continue
            eq = result.equipment[0]
            cad_block_id = eq.get("CAD_BLOCK_ID")

            if result.type != 'warning':
                if cad_block_id in equipment_error_map:
                    error_dict = {
                        "errorName": result.name,
                        "errorType": result.type,
                        "errorDescription": result.description
                    }
                    # 简单的去重检查
                    existing_names = [eem_dict['errorName'] for eem_dict in equipment_error_map[cad_block_id]]
                    if error_dict['errorName'] not in existing_names:
                        equipment_error_map[cad_block_id].append(error_dict)

        final_error_results = []
        for eq in errors_results:
            equipment = eq.equipment[0]
            _id = equipment.get("CAD_BLOCK_ID")
            if _id in equipment_error_map and len(equipment_error_map[_id]) > 0:
                eq.errors = equipment_error_map[_id]
                final_error_results.append(eq)

        final_warning_results = []
        # 这里原本有去重逻辑被注释掉了，保持原样直接 append
        for warning_data in warnings_results:
            final_warning_results.append(warning_data)

        # --- 阶段 6: 最终结果生成 (最可能的瓶颈) ---
        errors_num = {'field': 0, 'interface': 0}
        warning_num = {'field': 0, 'interface': 0}
        final_results = {'interfaces': [], 'field': []}

        # 处理 Errors
        if len(final_error_results) != 0:
            field_record = []
            interface_record = []

            for result in final_error_results:
                equipment = result.equipment[0]
                equipments = parse_block_attributes(equipment, filename)
                equipments = [{k.upper(): v for _equipment in equipments for k, v in _equipment.items()}]

                field_code = equipments[0].get('FIELD')
                # 注意：这里的 iloc 查询在循环中非常慢，如果数据量大，这里是主要瓶颈
                result_pd = field_pd[field_pd['FIELD.code'] == field_code]
                subsystem_id_df = subsystem_pd[subsystem_pd['SUBSYSTEM.code'] == equipments[0].get('SUB_SYSTEM')]

                if not result_pd.empty:
                    field_id = result_pd.iloc[0]['FIELD.id']
                else:
                    if result.operation == 'delete':
                        if len(equipments) == 0:
                            field_id = result.equipment[0].get('ID')
                        else:
                            field_id = None
                    else:
                        field_id = None

                if len(result.equipment) > 1:

                    if result.name == "ID.X唯一性错误":
                        final_results['interfaces'].append(_data)
                        interface_record.append(key)
                        errors_num['interface'] += 1
                        continue

                    result.equipment[0] = {k.upper(): v for k, v in result.equipment[0].items()}
                    result.equipment[1] = {k.upper(): v for k, v in result.equipment[1].items()}

                    _interface_pd = interface_pd[
                        interface_pd['INTERFACE.uni_code'] == f"{result.equipment[1].get('INTERFACE_CODE')}"]

                    search_id = result.equipment[-1].get('SEARCH_ID', '').replace('.', ';')
                    _data = {
                        'id': _interface_pd.iloc[0]['INTERFACE.id'] if not _interface_pd.empty else None,
                        'parent_id': '',
                        'field_id': field_id,
                        'fab_id': fab['id'],
                        'building_id': building['id'],
                        'building_level': building_level['name'],
                        'uniCode': f"{result.equipment[-1].get('INTERFACE_CODE')}",
                        'code': result.equipment[-1].get('ID'),
                        'field_code': f"{result.equipment[-1].get('SUB_SYSTEM') or ''}.{result.equipment[-1].get('BUILDING_LEVEL') or ''}.{result.equipment[-1].get('FIELD') or ''}",
                        'searchId': search_id,
                        'conSize': result.equipment[-1].get('CONNECTION_SIZE'),
                        'conType': result.equipment[-1].get('CONNECTION_TYPE'),
                        'maxDesignFlow': result.equipment[-1].get('DESIGN_FLOW'),
                        'unit': result.equipment[-1].get('FLOW_UNIT'),
                        'is_Assigned': None,
                        'chemicalName': result.equipment[-1].get('CHEMICAL_NAME') or result.equipment[-1].get(
                            'GAS_NAME'),
                        'isOutCode': None,
                        'locked': result.equipment[-1].get('locked'),
                        'layer': result.equipment[-1].get('LAYER'),
                        'insertPointX': result.equipment[-1].get('INSERT_POINT_X'),
                        'insertPointY': result.equipment[-1].get('INSERT_POINT_Y'),
                        'insertPointZ': result.equipment[-1].get('INSERT_POINT_Z'),
                        'angle': result.equipment[-1].get('ANGLE'),
                        'trueColor': result.equipment[-1].get('TRUE_COLOR'),
                        'cadBlockId': result.equipment[-1].get('CAD_BLOCK_ID'),
                        'cadBlockName': result.equipment[-1].get('CAD_BLOCK_NAME'),
                        'distributionBox': result.equipment[-1].get('DISTRIBUTION_BOX'),
                        'errors': result.errors
                    }
                    if not check_result_valid(_data):
                        raise Exception('check result is not valid')

                    key = f"{_data['uniCode']}-{_data['cadBlockId']}"
                    if key not in interface_record:
                        final_results['interfaces'].append(_data)
                        interface_record.append(key)
                        errors_num['interface'] += 1
                else:
                    # Field 处理逻辑
                    equipments = parse_block_attributes(result.equipment[0], filename)
                    equipments = [{k.upper(): v for k, v in eq_dict.items()} for eq_dict in equipments]
                    _equipment = equipments[0]

                    if len(str(_equipment.get('INSERT_POINT_X', ''))) < 2:
                        # 仅在调试时开启，生产环境可能不需要每次打印
                        # print(f"device={check_which_device(result.equipment[0], filename)}")
                        pass

                    field_code = _equipment.get('FIELD_CODE')
                    sub_system_code = _equipment.get('SUB_SYSTEM')

                    _field_pd = field_pd[field_pd['FIELD.uni_code'] == field_code]
                    _subsystem_pd = subsystem_pd[subsystem_pd['SUBSYSTEM.code'] == sub_system_code]

                    if not _field_pd.empty:
                        field_id = int(_field_pd.iloc[0]['FIELD.id'])
                    else:
                        field_id = None

                    if not _subsystem_pd.empty:
                        subsystem_id = int(_subsystem_pd.iloc[0]['SUBSYSTEM.id'])
                    else:
                        subsystem_id = None

                    search_id = _equipment.get('SEARCH_ID').replace('.', ';') if _equipment.get('SEARCH_ID') else ''

                    if result.device in ['TAKEOFF', 'NEW_INTER_']:
                        # Interface 处理逻辑 (嵌套在 else 中)
                        _interface_pd = interface_pd[
                            interface_pd['INTERFACE.uni_code'] == f"{result.equipment[-1].get('INTERFACE_CODE')}"]

                        _data = {
                            'id': _interface_pd.iloc[0]['INTERFACE.id'] if not _interface_pd.empty else None,
                            'parent_id': '',
                            'field_id': field_id,
                            'fab_id': fab['id'],
                            'building_id': building['id'],
                            'building_level': building_level['name'],
                            'uniCode': f"{_equipment.get('INTERFACE_CODE')}",
                            'code': _equipment.get('ID'),
                            'field_code': _equipment.get('FIELD_CODE'),
                            'searchId': search_id,
                            'conSize': _equipment.get('CONNECTION_SIZE'),
                            'conType': _equipment.get('CONNECTION_TYPE'),
                            'maxDesignFlow': _equipment.get('DESIGN_FLOW'),
                            'unit': _equipment.get('FLOW_UNIT'),
                            'is_Assigned': None,
                            'chemicalName': _equipment.get('CHEMICAL_NAME') or _equipment.get('GAS_NAME'),
                            'isOutCode': None,
                            'locked': _equipment.get('locked'),
                            'layer': _equipment.get('LAYER'),
                            'insertPointX': _equipment.get('INSERT_POINT_X'),
                            'insertPointY': _equipment.get('INSERT_POINT_Y'),
                            'insertPointZ': _equipment.get('INSERT_POINT_Z'),
                            'angle': _equipment.get('ANGLE'),
                            'trueColor': _equipment.get('TRUE_COLOR'),
                            'cadBlockId': _equipment.get('CAD_BLOCK_ID'),
                            'cadBlockName': _equipment.get('CAD_BLOCK_NAME'),
                            'distributionBox': _equipment.get('DISTRIBUTION_BOX'),
                            'errors': result.errors
                        }
                        key = f"{_data['uniCode']}-{_data['cadBlockId']}"
                        if key not in interface_record:
                            final_results['interfaces'].append(_data)
                            interface_record.append(key)
                            errors_num['interface'] += 1
                        continue

                    # 正常 Field 数据构建
                    field_data = {
                        'id': field_id,
                        'system_id': system['id'],
                        'subsystem_id': subsystem_id,
                        'fab_id': fab['id'],
                        'building_id': building['id'],
                        'building_level': building_level['name'],
                        'uniCode': f"{_equipment.get('SUB_SYSTEM') or ''}.{_equipment.get('BUILDING_LEVEL') or ''}.{_equipment.get('FIELD') or ''}",
                        'code': _equipment.get('FIELD'),
                        'searchId': search_id,
                        'conSize': _equipment.get('CONNECTION_SIZE') or result.equipment[0].get('SIZE'),
                        'conType': _equipment.get('CONNECTION_TYPE') or result.equipment[0].get('TYPE'),
                        'maxDesignFlow': _equipment.get('DESIGN_FLOW') or result.equipment[0].get('POS_MAX_FLOW'),
                        'unit': _equipment.get('FLOW_UNIT') if result.operation != 'delete' else result.equipment[
                            0].get('UNIT'),
                        'is_Assigned': None,
                        'isOutCode': None,
                        'locked': _equipment.get('locked') or result.equipment[0].get('LOCKED'),
                        'vmb_type': _equipment.get('VMB-TYPE') or result.equipment[0].get('VMB_TYPE'),
                        'layer': _equipment.get('LAYER') or result.equipment[0].get('LAYER'),
                        'insertPointX': _equipment.get('INSERT_POINT_X'),
                        'insertPointY': _equipment.get('INSERT_POINT_Y'),
                        'insertPointZ': _equipment.get('INSERT_POINT_Z'),
                        'angle': _equipment.get('ANGLE'),
                        'trueColor': _equipment.get('TRUE_COLOR'),
                        'cadBlockId': _equipment.get('CAD_BLOCK_ID'),
                        'cadBlockName': _equipment.get('CAD_BLOCK_NAME'),
                        'distributionBox': _equipment.get('DISTRIBUTION_BOX'),
                        'errors': result.errors
                    }

                    key = f"{field_data['uniCode']}-{field_data['cadBlockId']}"
                    if key not in field_record:
                        final_results['field'].append(field_data)
                        field_record.append(key)
                        errors_num['field'] += 1

            final_results = replace_nan_with_none(final_results)

            # 打个补丁， 将 append 到 field 中的 'ID.X唯一性错误' 错误类型 换到 interface
            # 处理 'ID.X唯一性错误' 类型错误，将field中的 'ID.X唯一性错误' 类型错误，添加到 interface 中
            for field_item in final_results['field']:
                idx_errors = [e for e in (field_item.get('errors') or []) if e.get('errorName') == 'ID.X唯一性错误']
                if not idx_errors:
                    continue
                matched = False
                for interface_item in final_results['interfaces']:
                    if interface_item.get('cadBlockId') == field_item.get('cadBlockId'):
                        if interface_item.get('errors') is None:
                            interface_item['errors'] = []
                        interface_item['errors'].extend(idx_errors)
                        matched = True
                if not matched:
                    new_interface = {
                        'id': None,
                        'parent_id': '',
                        'field_id': field_item.get('id'),
                        'fab_id': field_item.get('fab_id'),
                        'building_id': field_item.get('building_id'),
                        'building_level': field_item.get('building_level'),
                        'uniCode': field_item.get('searchId') if ('.' in str(field_item.get('uniCode') or '')) else field_item.get('uniCode'),
                        'code': field_item.get('code'),
                        'field_code': field_item.get('uniCode'),
                        'searchId': field_item.get('searchId') if field_item.get('cadBlockName').startswith('VMB') else field_item.get('searchId').split(';')[2],
                        'conSize': field_item.get('conSize'),
                        'conType': field_item.get('conType'),
                        'maxDesignFlow': field_item.get('maxDesignFlow'),
                        'unit': field_item.get('unit'),
                        'is_Assigned': None,
                        'chemicalName': field_item.get('chemicalName'),
                        'isOutCode': None,
                        'locked': field_item.get('locked'),
                        'layer': field_item.get('layer'),
                        'insertPointX': field_item.get('insertPointX'),
                        'insertPointY': field_item.get('insertPointY'),
                        'insertPointZ': field_item.get('insertPointZ'),
                        'angle': field_item.get('angle'),
                        'trueColor': field_item.get('trueColor'),
                        'cadBlockId': field_item.get('cadBlockId'),
                        'cadBlockName': field_item.get('cadBlockName'),
                        'distributionBox': field_item.get('distributionBox'),
                        'errors': idx_errors
                    }
                    final_results['interfaces'].append(new_interface)
                field_item['errors'] = [e for e in (field_item.get('errors') or []) if
                                        e.get('errorName') != 'ID.X唯一性错误']

            # 处理 '必填项未填写: {field}' 类型错误，将field中的 '必填项未填写: {field}' 类型错误，添加到 interface 中
            _interface_field_prefixes = ('ID.', 'CS.', 'CT.')
            fields_to_remove = []
            for field_item in final_results['field']:
                all_errors = field_item.get('errors') or []
                interface_required_errors = [
                    e for e in all_errors
                    if e.get('errorName') == '必填项缺失'
                    and any(prefix in e.get('errorDescription', '') for prefix in _interface_field_prefixes)
                ]
                if not interface_required_errors:
                    continue

                all_migrated = len(interface_required_errors) == len(all_errors)

                matched = False
                for interface_item in final_results['interfaces']:
                    if interface_item.get('cadBlockId') == field_item.get('cadBlockId'):
                        if interface_item.get('errors') is None:
                            interface_item['errors'] = []
                        interface_item['errors'].extend(interface_required_errors)
                        matched = True
                if not matched:
                    new_interface = {
                        'id': None,
                        'parent_id': '',
                        'field_id': field_item.get('id'),
                        'fab_id': field_item.get('fab_id'),
                        'building_id': field_item.get('building_id'),
                        'building_level': field_item.get('building_level'),
                        'uniCode': field_item.get('searchId'),
                        'code': field_item.get('code'),
                        'field_code': field_item.get('uniCode'),
                        'searchId': field_item.get('searchId'),
                        'conSize': field_item.get('conSize'),
                        'conType': field_item.get('conType'),
                        'maxDesignFlow': field_item.get('maxDesignFlow'),
                        'unit': field_item.get('unit'),
                        'is_Assigned': None,
                        'chemicalName': field_item.get('chemicalName'),
                        'isOutCode': None,
                        'locked': field_item.get('locked'),
                        'layer': field_item.get('layer'),
                        'insertPointX': field_item.get('insertPointX'),
                        'insertPointY': field_item.get('insertPointY'),
                        'insertPointZ': field_item.get('insertPointZ'),
                        'angle': field_item.get('angle'),
                        'trueColor': field_item.get('trueColor'),
                        'cadBlockId': field_item.get('cadBlockId'),
                        'cadBlockName': field_item.get('cadBlockName'),
                        'distributionBox': field_item.get('distributionBox'),
                        'errors': interface_required_errors
                    }
                    final_results['interfaces'].append(new_interface)

                if all_migrated:
                    fields_to_remove.append(field_item)
                else:
                    field_item['errors'] = [
                        e for e in all_errors
                        if not (
                            e.get('errorName') == '必填项缺失'
                            and any(prefix in e.get('errorDescription', '') for prefix in _interface_field_prefixes)
                        )
                    ]
            for _f in fields_to_remove:
                final_results['field'].remove(_f)


            return_result = {
                'code': 200,
                'message': "调用成功",
                'success': False,
                'data': final_results
            }

        # 处理 Warnings
        elif len(final_warning_results) != 0:
            field_record = []
            interface_record = []

            for result in final_warning_results:
                equipment = result.equipment[0]
                last_equipment = equipment
                equipments = parse_block_attributes(equipment, filename)
                equipment = [{k.upper(): v for _equipment in equipments for k, v in _equipment.items()}][0]

                field_code = equipment.get('FIELD_CODE')
                sub_system_code = equipment.get('SUB_SYSTEM')

                result_pd = field_pd[field_pd['FIELD.uni_code'] == field_code]
                subsystem_id_df = subsystem_pd[subsystem_pd['SUBSYSTEM.code'] == equipment.get('SUB_SYSTEM')]

                if not result_pd.empty:
                    field_id = result_pd.iloc[0]['FIELD.id']
                else:
                    if result.operation == 'delete':
                        if len(equipments) == 0:
                            field_id = result.equipment[0].get('ID')
                        else:
                            field_id = None
                    else:
                        field_id = None

                if not subsystem_id_df.empty:
                    subsystem_id = subsystem_id_df.iloc[0]['SUBSYSTEM.id']
                else:
                    if result.operation == 'delete':
                        if len(equipments) == 0:
                            subsystem_id = result.equipment[0].get('SUBSYSTEM_ID')
                        else:
                            subsystem_id = None
                    else:
                        subsystem_id = None

                if len(result.equipment) > 1:
                    # Interface 处理
                    for _re_i in range(len(result.equipment)):
                        result.equipment[_re_i] = {k.upper(): v for k, v in result.equipment[_re_i].items()}

                    _interface_pd = interface_pd[
                        interface_pd['INTERFACE.uni_code'] == f"{result.equipment[-1].get('INTERFACE_CODE')}"]

                    if not _interface_pd.empty:
                        interface_id = _interface_pd.iloc[0]['INTERFACE.id']
                    else:
                        if result.operation == 'delete':
                            if len(equipments) == 0:
                                interface_id = None
                            else:
                                interface_id = result.equipment[-1].get('ID')
                        else:
                            interface_id = None

                    if result.operation == 'add':
                        field_name = result.equipment[1]['FIELD']
                        _field_pd = field_pd[field_pd['FIELD.code'] == field_name]
                        if not _field_pd.empty:
                            field_id = _field_pd.iloc[0]['FIELD.id']

                    if result.operation == 'delete':
                        search_id = parse_search_id(result, system)
                    else:
                        search_id = result.equipment[-1].get('SEARCH_ID')

                    search_id = search_id.replace('.', ';') if search_id else ''

                    _data = {
                        'id': interface_id if interface_id != 'None' else int(
                            interface_id) if interface_id is not None else None,
                        'parent_id': '',
                        'field_id': field_id if result.operation != 'delete' else result.equipment[-1].get('FIELD_ID'),
                        'fab_id': fab['id'],
                        'building_id': building['id'],
                        'building_level': building_level['name'],
                        'uniCode': result.equipment[-1].get('INTERFACE_CODE') if result.operation != 'delete' else
                        result.equipment[-1].get('UNI_CODE'),
                        'code': result.equipment[-1].get('id'),
                        'field_code': f"{result.equipment[-1].get('SUB_SYSTEM') or ''}.{result.equipment[-1].get('BUILDING_LEVEL') or ''}.{result.equipment[-1].get('FIELD') or ''}" \
                            if result.operation != 'delete' else (result.equipment[0].get('UNI_CODE') or ''),
                        'searchId': search_id,
                        'conSize': result.equipment[-1].get('CONNECTION_SIZE'),
                        'conType': result.equipment[-1].get('CONNECTION_TYPE'),
                        'maxDesignFlow': result.equipment[-1].get('DESIGN_FLOW'),
                        'unit': result.equipment[-1].get('FLOW_UNIT'),
                        'is_Assigned': None,
                        'chemicalName': result.equipment[-1].get('CHEMICAL_NAME') or result.equipment[-1].get(
                            'GAS_NAME'),
                        'isOutCode': None,
                        'locked': result.equipment[-1].get('locked'),
                        'layer': result.equipment[-1].get('LAYER'),
                        'insertPointX': result.equipment[-1].get('INSERT_POINT_X'),
                        'insertPointY': result.equipment[-1].get('INSERT_POINT_Y'),
                        'insertPointZ': result.equipment[-1].get('INSERT_POINT_Z'),
                        'angle': result.equipment[-1].get('ANGLE'),
                        'trueColor': result.equipment[-1].get('TRUE_COLOR'),
                        'cadBlockId': result.equipment[-1].get('CAD_BLOCK_ID'),
                        'cadBlockName': result.equipment[-1].get('CAD_BLOCK_NAME'),
                        'distributionBox': result.equipment[-1].get('DISTRIBUTION_BOX'),
                        'operation': result.operation,
                        'detail': result.detail
                    }

                    if not check_result_valid(_data):
                        raise Exception('check result is not valid')

                    key = f"{_data['uniCode']}-{_data['operation']}-{_data['cadBlockId']}"
                    if key not in interface_record:
                        final_results['interfaces'].append(_data)
                        interface_record.append(key)
                        warning_num['interface'] += 1
                else:
                    # Field 处理
                    if result.operation == 'delete':
                        search_id = parse_search_id(result, system)
                    else:
                        search_id = equipment.get('SEARCH_ID') or ''

                    search_id = search_id.replace('.', ';')

                    field_data = {
                        'id': field_id if result.operation != 'delete' else result.equipment[0].get('ID'),
                        'system_id': system['id'],
                        'subsystem_id': subsystem_id if result.operation != 'delete' else result.equipment[0].get(
                            'SUBSYSTEM_ID'),
                        'fab_id': fab['id'],
                        'building_id': building['id'],
                        'building_level': building_level['name'],
                        'uniCode': f"{equipment.get('SUB_SYSTEM') or ''}.{equipment.get('BUILDING_LEVEL') or ''}.{equipment.get('FIELD') or ''}" \
                            if result.operation != 'delete' else (result.equipment[0].get('UNI_CODE') or ''),
                        'code': equipment.get('FIELD') if result.operation != 'delete' else result.equipment[0].get(
                            'CODE'),
                        'chemical_name': equipment.get('CHEMICAL_NAME') or equipment.get('GAS_NAME'),
                        'searchId': search_id,
                        'conSize': equipment.get('CONNECTION_SIZE') if result.operation != 'delete' else
                        result.equipment[0].get('SIZE'),
                        'conType': equipment.get('CONNECTION_TYPE') if result.operation != 'delete' else
                        result.equipment[0].get('TYPE'),
                        'maxDesignFlow': equipment.get('DESIGN_FLOW') if result.operation != 'delete' else
                        result.equipment[0].get('POS_MAX_FLOW'),
                        'unit': equipment.get('FLOW_UNIT') if result.operation != 'delete' else result.equipment[0].get(
                            'UNIT'),
                        'is_Assigned': None,
                        'isOutCode': None,
                        'locked': equipment.get('locked') if result.operation != 'delete' else result.equipment[0].get(
                            'LOCKED'),
                        'vmb_type': equipment.get('VMB-TYPE') if result.operation != 'delete' else result.equipment[
                            0].get('VMB_TYPE'),
                        'layer': equipment.get('LAYER') if result.operation != 'delete' else result.equipment[0].get(
                            'LAYER'),
                        'insertPointX': equipment.get('INSERT_POINT_X') if result.operation != 'delete' else
                        result.equipment[0].get('INSERT_POINT_X'),
                        'insertPointY': equipment.get('INSERT_POINT_Y') if result.operation != 'delete' else
                        result.equipment[0].get('INSERT_POINT_Y'),
                        'insertPointZ': equipment.get('INSERT_POINT_Z') if result.operation != 'delete' else
                        result.equipment[0].get('INSERT_POINT_Z'),
                        'angle': equipment.get('ANGLE') if result.operation != 'delete' else result.equipment[0].get(
                            'ANGLE'),
                        'trueColor': equipment.get('TRUE_COLOR') if result.operation != 'delete' else result.equipment[
                            0].get('TRUE_COLOR'),
                        'cadBlockId': equipment.get('CAD_BLOCK_ID') if result.operation != 'delete' else
                        result.equipment[0].get('CAD_BLOCK_ID'),
                        'cadBlockName': equipment.get('CAD_BLOCK_NAME') if result.operation != 'delete' else
                        result.equipment[0].get('CAD_BLOCK_NAME'),
                        'distributionBox': equipment.get('DISTRIBUTION_BOX') if result.operation != 'delete' else
                        result.equipment[0].get('DISTRIBUTION_BOX'),
                        'operation': result.operation,
                        'detail': result.detail
                    }

                    if not check_result_valid(field_data):
                        raise Exception('check result is not valid')

                    key = f"{field_data['uniCode']}-{field_data['operation']}"
                    if key not in field_record:
                        field_record.append(key)
                        final_results['field'].append(field_data)
                        warning_num['field'] += 1

            final_results = replace_nan_with_none(final_results)

            # 统计操作类型
            final_results['interfaces_add'] = 0
            final_results['interfaces_delete'] = 0
            final_results['interfaces_update'] = 0
            final_results['fields_add'] = 0
            final_results['fields_delete'] = 0
            final_results['fields_update'] = 0

            for r in final_results['interfaces']:
                op = r.get('operation')
                if op == 'add':
                    final_results['interfaces_add'] += 1
                elif op == 'update':
                    final_results['interfaces_update'] += 1
                elif op == 'delete':
                    final_results['interfaces_delete'] += 1
            final_results['interfaces_num'] = len(final_results['interfaces'])

            for r in final_results['field']:
                op = r.get('operation')
                if op == 'add':
                    final_results['fields_add'] += 1
                elif op == 'update':
                    final_results['fields_update'] += 1
                elif op == 'delete':
                    final_results['fields_delete'] += 1
            final_results['field_nums'] = len(final_results['field'])

            return_result = {
                'code': 200,
                'message': "调用成功",
                'success': True,
                'data': final_results
            }

        else:
            # 无错误无警告
            return_result = {
                'code': 200,
                'message': "调用成功",
                'success': True,
                'data': final_results
            }

        return return_result

    except Exception as e:
        return {
            "code": 400,
            "message": f"算法调用失败：{str(e)}",
            "traceback": traceback.format_exc()
        }


if __name__ == "__main__":
    # YMTC\Fab1\_Equipment\_Layout\_Archive\YMTC^ELD^WS^F1_20260306134218.dxf
    pass
