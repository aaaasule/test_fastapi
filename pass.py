"""
SLD 校验主流程：解析 → 规范性 → 柱网 → 变更 → 组装返回体。
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.config import logger
from app.sld.grid import SldGridMatcher
from app.sld.models import SldDevice, SldFileContext, SldIssue
from app.sld.parser import parse_sld_dxf
from app.sld.validators import (
    build_deleted_devices,
    business_key,
    run_change_checks,
    run_spec_checks,
)
from app.sld.validators.changes.common import build_history_index


def _json_param(val: Any) -> Any:
    if isinstance(val, (dict, list)):
        return val
    return json.loads(val) if isinstance(val, str) else val


def _first_val(row: Dict[str, Any], *keys: str) -> Any:
    """从字典中取第一个存在的非 None 值。"""
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return None


def _index_equipment_by_code(equipment_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """equipmentList 按 ``code`` 索引（与图面 ``id_equ`` 匹配）；同 code 保留首条。"""
    out: Dict[str, Dict[str, Any]] = {}
    for item in equipment_list or []:
        c = str(item.get("code") or "").strip()
        if c and c not in out:
            out[c] = item
    return out


def _attach_source_rows(
    devices: List[SldDevice],
    eld_sub_list: List[Dict[str, Any]],
    equipment_list: List[Dict[str, Any]],
) -> None:
    """为输出回带 id/fabId 等：更新/未改匹配 eldSubEquipmentList；新增匹配 equipmentList.code。"""
    eld_idx = build_history_index(eld_sub_list)
    eq_by_code = _index_equipment_by_code(equipment_list)
    for d in devices:
        k = business_key(d)
        if k and k != "+" and k in eld_idx.by_biz:
            d.eld_source_row = eld_idx.by_biz[k]
            continue
        if d.operation == "add":
            ie = (d.id_equ or "").strip()
            if ie and ie in eq_by_code:
                d.equipment_source_row = eq_by_code[ie]


def _merge_db_fields_into_eqp(base: Dict[str, Any], d: SldDevice) -> None:
    """合并数据库主键与归属字段到 eqp 输出（优先 eld 行，新增仅 equipment 行）。"""
    row = d.eld_source_row
    eq = d.equipment_source_row
    if row:
        mapping = (
            ("id", ("id",)),
            ("fabId", ("fabId", "fab_id")),
            ("buildingId", ("buildingId", "building_id")),
            ("buildingLevel", ("buildingLevel", "building_level")),
            ("groupId", ("groupId", "group_id")),
            ("equipmentId", ("equipmentId", "equipment_id")),
        )
        for out_key, keys in mapping:
            v = _first_val(row, *keys)
            if v is not None:
                base[out_key] = v
    elif eq:
        v = _first_val(eq, "id")
        if v is not None:
            base["equipmentId"] = v
        v = _first_val(eq, "fabId", "fab_id")
        if v is not None:
            base["fabId"] = v
        v = _first_val(eq, "buildingId", "building_id")
        if v is not None:
            base["buildingId"] = v
        v = _first_val(eq, "groupId", "group_id")
        if v is not None:
            base["groupId"] = v


def _token(obj: Dict[str, Any], prefer_code: bool = True) -> str:
    if prefer_code and obj.get("code") is not None:
        return str(obj.get("code")).strip()
    if obj.get("id") is not None:
        return str(obj.get("id")).strip()
    return ""


def _allowed_owner_codes(equipment_group_list: List[dict], building_level: dict) -> Set[str]:
    b_id = building_level.get("buildingId")
    out: Set[str] = set()
    for row in equipment_group_list:
        if b_id is not None and row.get("buildingId") != b_id:
            continue
        c = row.get("code")
        if c:
            out.add(str(c).strip().upper())
    return out


def _issue_to_diff_line(issue: SldIssue) -> str:
    """单条 warning/error issue 转为 diffContent 描述行。"""
    return f"{issue.name} | {issue.description} | {json.dumps(issue.detail, ensure_ascii=False)}"


def _merge_eqp_into_diff_content(
    eqp_data: List[Dict[str, Any]],
    devices_in_order: List[SldDevice],
    warnings: List[SldIssue],
) -> List[Dict[str, Any]]:
    """用 diff 描述行替换每台设备行的 ``description``，作为 ``diffContent`` 输出（不再单独返回 eqpData）。"""
    last_line_by_dev: Dict[int, str] = {}
    delete_line_by_key: Dict[str, str] = {}
    orphan_lines: List[str] = []

    for issue in warnings:
        line = _issue_to_diff_line(issue)
        d = issue.device
        if d is not None:
            last_line_by_dev[id(d)] = line
            continue
        biz_key = str(issue.detail.get("ID_EQU+ID_EquSubShort") or "").strip()
        if issue.name == "设备删除" and biz_key:
            delete_line_by_key[biz_key] = line
        else:
            orphan_lines.append(line)

    out: List[Dict[str, Any]] = []
    assert len(eqp_data) == len(devices_in_order)
    for row, d in zip(eqp_data, devices_in_order):
        merged = dict(row)
        line = last_line_by_dev.get(id(d))
        if line is None and merged.get("operation") == "delete":
            line = delete_line_by_key.get(business_key(d))
        merged["description"] = line
        out.append(merged)

    for line in orphan_lines:
        out.append({"description": line})

    return out


def _build_error_data_per_device(
    devices: List[SldDevice],
    deleted_devices: List[SldDevice],
    error_issues: List[SldIssue],
) -> List[Dict[str, Any]]:
    """异常路径：每台命中 error 的设备一行 + errors[]（对齐 ELD 风格）。

    - 设备身份键用 ``id(device)``，与 ``issue.device`` 同对象时直接命中
      （避免业务键空 / 重复时的歧义）。
    - 同一台设备的多条 error 会合并到 ``errors`` 列表，按 description 去重。
    - 没有 device 关联的 error（如文件名错误、唯一性聚合错误）合并为
      一行"全局错误虚拟设备行"（所有设备字段为 None）放在末尾。
    - 异常路径不输出 ``operation``。
    """
    by_dev: Dict[int, List[Dict[str, Any]]] = {}
    seen_desc: Dict[int, set] = {}
    global_errors: List[Dict[str, Any]] = []
    seen_global_desc: set = set()

    for issue in error_issues:
        item = {
            "errorName": issue.name,
            "errorType": issue.type,
            "errorDescription": issue.description,
        }
        d = issue.device
        if d is None:
            if issue.description in seen_global_desc:
                continue
            seen_global_desc.add(issue.description)
            global_errors.append(item)
            continue
        key = id(d)
        by_dev.setdefault(key, [])
        seen_desc.setdefault(key, set())
        if issue.description in seen_desc[key]:
            continue
        seen_desc[key].add(issue.description)
        by_dev[key].append(item)

    out: List[Dict[str, Any]] = []
    for d in list(devices) + list(deleted_devices):
        errs = by_dev.get(id(d))
        if not errs:
            continue
        row = device_to_eqp_dict(d)
        row.pop("operation", None)
        row["errors"] = errs
        out.append(row)

    if global_errors:
        empty = {k: None for k in device_to_eqp_dict(SldDevice()).keys()}
        empty.pop("operation", None)
        empty["errors"] = global_errors
        out.append(empty)

    return out


def device_to_eqp_dict(d: SldDevice) -> Dict[str, Any]:
    """转为 API camelCase 单条设备。

    ``operation`` 表达本设备相对于上一版的变更：
    ``"add" / "update" / "delete"``，无变更则为 ``None``。
    """
    base = {
        "idEqu": d.id_equ,
        "idEquSubShort": d.id_equ_sub_short,
        "equipmentCode": d.id_equ,
        "equSubShort": d.id_equ_sub_short,
        "toolId": d.tool_id,
        "owner": d.owner,
        "vendor": d.vendor,
        "model": d.model,
        "bayLocation": d.bay_location,
        "records": d.records,
        "blockName": d.block_name,
        "gridX": d.grid_x,
        "gridY": d.grid_y,
        "layer": d.layer,
        "angle": d.angle,
        "trueColor": d.true_color,
        "insertPointX": d.insert_point_x,
        "insertPointY": d.insert_point_y,
        "insertPointZ": d.insert_point_z,
        "centerPointX": d.center_point_x,
        "centerPointY": d.center_point_y,
        "centerPointZ": d.center_point_z,
        "blockId": d.block_id,
        "operation": d.operation,
    }
    _merge_db_fields_into_eqp(base, d)
    return base


def run_sld_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    params 与 exec_config.json 一致：
      file_path, company, fab, building, buildingLevel,
      equipmentList, eldSubEquipmentList（或旧名 equipmentGroupList）, layerList, gridList,
      cache_folder, mission_start_time

    变更对比基准为 **eldSubEquipmentList**；**equipmentList** 仅用于新增行按 ``code`` 与
    图面 ``id_equ`` 匹配后回带 ``fabId/buildingId/groupId/equipmentId``。
    """
    cache_folder = params.get("cache_folder", ".")
    mission_start_time = params.get("mission_start_time", "")
    logger.info(
        "[SLD] 开始校验 mission_start_time=%s cache_folder=%s",
        mission_start_time,
        cache_folder,
    )

    try:
        file_path = params.get("file_path") or params.get("file")
        if not file_path:
            return {
                "code": 400,
                "message": "file_path 或 file 不能为空",
                "success": False,
                "data": [{"errors": ["file_path 或 file 不能为空"]}],
            }
        company = _json_param(params["company"])
        fab = _json_param(params.get("fab", {}))
        building = _json_param(params["building"])
        building_level = _json_param(params["buildingLevel"])
        equipment_list = _json_param(params.get("equipmentList", []))
        eld_sub_equipment_list = _json_param(
            params.get("eldSubEquipmentList") or params.get("equipmentGroupList", [])
        )
        layer_list = _json_param(params.get("layerList", []))
        grid_list = _json_param(params.get("gridList", []))
        logger.info(
            "[SLD] 参数解析完成 file_path=%s company=%s fab=%s building=%s level=%s "
            "equipment_count=%s eld_sub_count=%s layer_count=%s grid_count=%s",
            file_path,
            company.get("code") or company.get("id"),
            fab.get("code") or fab.get("id"),
            building.get("code") or building.get("id"),
            building_level.get("code") or building_level.get("id"),
            len(equipment_list or []),
            len(eld_sub_equipment_list or []),
            len(layer_list or []),
            len(grid_list or []),
        )

        stem = Path(file_path).stem
        company_token = _token(company)
        building_token = _token(building)
        level_token = str(building_level.get("code", "")).strip()

        allowed = _allowed_owner_codes(eld_sub_equipment_list or [], building_level)
        ctx = SldFileContext(
            file_path=file_path,
            filename_stem=stem,
            company_token=company_token,
            building_token=building_token,
            level_token=level_token,
            allowed_owner_codes=frozenset(allowed),
        )

        layer_codes: Optional[List[str]] = None
        if layer_list:
            layer_codes = [str(x.get("code", x)).strip() for x in layer_list if str(x.get("code", x)).strip()]
        logger.info("[SLD] 文件上下文初始化完成 stem=%s layer_codes=%s", stem, layer_codes)

        try:
            logger.info("[SLD] 开始读取并解析 DXF file_path=%s", file_path)
            devices = parse_sld_dxf(file_path, target_layers=layer_codes)
            logger.info("[SLD] DXF 解析完成 device_count=%s", len(devices))
        except Exception as e:
            logger.exception("[SLD] DXF 文件读取或解析失败 file_path=%s", file_path)
            return {
                "code": 400,
                "message": f"DXF 文件读取或解析失败: {e}",
                "success": False,
                "data": [{"errors": [str(e)]}],
            }

        # 解析缓存（大文件可二次排查）
        try:
            cache_path = Path(cache_folder) / f"parser_{mission_start_time}.json"
            serializable = [asdict(d) for d in devices]
            cache_path.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("[SLD] 解析缓存写入完成 cache_path=%s", cache_path)
        except Exception as e:
            logger.exception("[SLD] 解析缓存写入失败 cache_folder=%s error=%s", cache_folder, e)

        issues = []
        logger.info("[SLD] 开始执行规范性校验")
        issues.extend(run_spec_checks(ctx, devices))
        logger.info("[SLD] 规范性校验完成 issue_count=%s", len(issues))

        if grid_list:
            try:
                logger.info("[SLD] 开始执行柱网匹配 grid_count=%s", len(grid_list))
                matcher = SldGridMatcher(grid_list)
                matcher.apply_to_devices(devices)
                logger.info("[SLD] 柱网匹配完成")
            except Exception as ge:
                logger.exception("[SLD] 柱网匹配失败")
                issues.append(
                    SldIssue(
                        type="warning",
                        name="柱网匹配失败",
                        description=str(ge),
                        detail={"exception": str(ge)},
                    )
                )
        else:
            logger.info("[SLD] 未提供柱网数据，跳过柱网匹配")

        before_change_issue_count = len(issues)
        logger.info(
            "[SLD] 开始执行变更校验 eld_sub_count=%s equipment_count=%s",
            len(eld_sub_equipment_list or []),
            len(equipment_list or []),
        )
        issues.extend(run_change_checks(devices, eld_sub_equipment_list or []))
        logger.info(
            "[SLD] 变更校验完成 new_issue_count=%s total_issue_count=%s",
            len(issues) - before_change_issue_count,
            len(issues),
        )

        # 构造 operation="delete" 的"幽灵设备"，追加到 eqpData 输出，
        # 让前端可以拿到完整的 add/update/delete 集合（与 ELD 对齐）。
        deleted_devices = build_deleted_devices(devices, eld_sub_equipment_list or [])
        logger.info("[SLD] 删除幽灵设备构造完成 deleted_count=%s", len(deleted_devices))

        _attach_source_rows(devices, eld_sub_equipment_list or [], equipment_list or [])

        errors = [i for i in issues if i.type == "error"]
        warnings = [i for i in issues if i.type == "warning"]
        logger.info(
            "[SLD] 校验结果汇总 error_count=%s warning_count=%s device_count=%s deleted_count=%s",
            len(errors),
            len(warnings),
            len(devices),
            len(deleted_devices),
        )

        has_error = len(errors) > 0
        if has_error:
            error_data = _build_error_data_per_device(devices, deleted_devices, errors)
            logger.info(
                "[SLD] 校验结束 success=False error_row_count=%s",
                len(error_data),
            )
            return {
                "code": 200,
                "message": "调用成功",
                "success": False,
                "data": error_data,
            }

        # 成功路径：data 仅含 diffContent；每条为原 eqpData 设备行，
        # description 替换为对应 warning 的 diff 描述行（未变更设备为 null）。
        devices_in_order: List[SldDevice] = list(devices) + list(deleted_devices)
        eqp_data = [device_to_eqp_dict(d) for d in devices_in_order]
        diff_content = _merge_eqp_into_diff_content(eqp_data, devices_in_order, warnings)

        logger.info("[SLD] 校验结束 success=True diff_content_count=%s", len(diff_content))
        return {
            "code": 200,
            "message": "调用成功",
            "success": True,
            "data": [{"diffContent": diff_content}],
        }
    except Exception as e:
        logger.exception("[SLD] 校验流程异常 mission_start_time=%s", mission_start_time)
        return {
            "code": 400,
            "message": f"算法调用失败: {str(e)}",
            "success": False,
            "data": [{"errors": [str(e)]}],
        }


def run_sld_check_from_config_path(config_path: str) -> Dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        params = json.load(f)
    params["cache_folder"] = str(Path(config_path).parent)
    return run_sld_check(params)
