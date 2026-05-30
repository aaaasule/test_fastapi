#/app/fid/api.py
import datetime
import json
import shutil
import subprocess
import sys
import time
import traceback
import asyncio

import re
from pathlib import Path, PurePosixPath

from fastapi import File, Form, UploadFile, APIRouter, BackgroundTasks
import ezdxf

#from app.config import fid_config as config
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

from app.config import logger, write_fid_logger, fid_config as config
from app.fid.utils.log_manage import cleanup_old_logs
#from app.config.fid_config import FTP_CONFIG
from app.fid.utils.ftp_download import download_file_from_ftp, upload_file_to_ftp
from app.fid.utils.write_fid_writer import (
    apply_takeoff_colors,
    build_write_fid_ftp_result_names,
    clear_equ_attributes,
    write_equipment_code,
)
from app.fid.schemas import WriteFidRequest, WriteFidResponse

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
from app.config.fid_config import FTP_CONFIG, build_eld_callback_url, build_fid_callback_url
from app.util import make_async_accept_response, make_task_error_response, run_sync_task_with_callback

router = APIRouter()


async def _prepare_file_payload(file: UploadFile | str) -> dict:
    if isinstance(file, str):
        return {"source": "ftp", "remote_path": file}
    return {
        "source": "upload",
        "filename": file.filename or "upload.dxf",
        "content": await file.read(),
    }


def _save_dxf_from_payload(file_payload: dict, work_dir: Path, start_time: str) -> Path:
    if file_payload["source"] == "upload":
        stem = Path(file_payload["filename"]).stem
        work_dir.mkdir(parents=True, exist_ok=True)
        file_path = work_dir / f"{stem}_{start_time}.dxf"
        with open(file_path, "wb") as f:
            f.write(file_payload["content"])
        return file_path.absolute()

    remote_path = file_payload["remote_path"]
    stem = Path(remote_path).stem
    work_dir.mkdir(parents=True, exist_ok=True)
    file_path = work_dir / f"{stem}_{start_time}.dxf"
    download_file_from_ftp(
        host=FTP_CONFIG["host"],
        username=FTP_CONFIG["username"],
        password=FTP_CONFIG["password"],
        port=FTP_CONFIG["port"],
        local_file_path=str(file_path),
        remote_filename=remote_path,
    )
    return file_path.absolute()


def _run_check_subprocess(exec_config_path: Path, cli_script: str, start_time: str) -> dict:
    log_file = exec_config_path.parent / f"{start_time}.log"
    cmd = [
        sys.executable,
        "-u",
        str(Path(__file__).parent / cli_script),
        str(exec_config_path.absolute()),
    ]
    with open(log_file, "w", encoding="utf-8") as log_f:
        proc = subprocess.run(cmd, stdout=log_f, stderr=subprocess.STDOUT, text=True)
    returncode = proc.returncode

    result_path = exec_config_path.parent / f"result_{start_time}.json"
    if result_path.is_file():
        with open(result_path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "code": 400,
        "message": f"子进程未生成结果(returncode={returncode})，日志: {log_file}",
        "success": False,
        "data": [{"errors": [f"子进程 returncode={returncode}"]}],
    }


def _run_eld_check_sync(file_payload: dict, form_params: dict, start_time: str) -> dict:
    remote_or_name = (
        file_payload["remote_path"]
        if file_payload["source"] == "ftp"
        else file_payload["filename"]
    )
    filename = re.sub("[^a-zA-Z0-9]", "", Path(remote_or_name).stem)
    work_dir = Path(config.UPLOAD_DIR) / f"eld_{filename}"
    file_path = _save_dxf_from_payload(file_payload, work_dir, start_time)

    exec_config_path = work_dir / f"exec_config_{start_time}.json"
    config_json = {
        "file_path": str(file_path),
        "company": json.loads(form_params["company"]),
        "fab": json.loads(form_params["fab"]),
        "building": json.loads(form_params["building"]),
        "buildingLevel": json.loads(form_params["buildingLevel"]),
        "equipmentList": json.loads(form_params["equipmentList"]),
        "equipmentGroupList": json.loads(form_params["equipmentGroupList"]),
        "layerList": json.loads(form_params["layerList"]),
        "gridList": json.loads(form_params["gridList"]),
        "mode": form_params.get("mode", "default"),
        "mission_start_time": start_time,
        "uploadSessionToken": form_params.get("uploadSessionToken", ""),
    }
    exec_config_path.parent.mkdir(parents=True, exist_ok=True)
    exec_config_path.write_text(json.dumps(config_json, ensure_ascii=False, indent=4), encoding="utf-8")
    return _run_check_subprocess(exec_config_path, "eld_check_cli.py", start_time)


def _run_fid_check_sync(file_payload: dict, form_params: dict, start_time: str) -> dict:
    remote_or_name = (
        file_payload["remote_path"]
        if file_payload["source"] == "ftp"
        else file_payload["filename"]
    )
    filename = re.sub("[^a-zA-Z0-9]", "", Path(remote_or_name).stem)
    work_dir = Path(config.UPLOAD_DIR) / f"fid_{filename}"
    file_path = _save_dxf_from_payload(file_payload, work_dir, start_time)

    exec_config_path = work_dir / f"exec_config_{start_time}.json"
    config_json = {
        "file_path": str(file_path),
        "company": json.loads(form_params["company"]),
        "fab": json.loads(form_params["fab"]),
        "building": json.loads(form_params["building"]),
        "buildingLevel": json.loads(form_params["buildingLevel"]),
        "system": json.loads(form_params["system"]),
        "subsystemList": json.loads(form_params["subsystemList"]),
        "fieldList": json.loads(form_params["fieldList"]),
        "interfaceList": json.loads(form_params["interfaceList"]),
        "systemInterfaceList": json.loads(form_params["systemInterfaceList"]),
        "mode": form_params.get("mode", "default"),
        "mission_start_time": start_time,
        "uploadSessionToken": form_params.get("uploadSessionToken", ""),
    }
    exec_config_path.parent.mkdir(parents=True, exist_ok=True)
    exec_config_path.write_text(json.dumps(config_json, ensure_ascii=False, indent=4), encoding="utf-8")
    result = _run_check_subprocess(exec_config_path, "fid_check_cli.py", start_time)
    cleanup_old_logs(config.UPLOAD_DIR, config.MEMORY_LIMIT)
    return result


async def _eld_check_background(file_payload: dict, form_params: dict, upload_session_token: str, start_time: str) -> None:
    await run_sync_task_with_callback(
        lambda: _run_eld_check_sync(file_payload, form_params, start_time),
        upload_session_token,
        build_eld_callback_url(),
        log_tag="ELD",
    )


async def _fid_check_background(file_payload: dict, form_params: dict, upload_session_token: str, start_time: str) -> None:
    await run_sync_task_with_callback(
        lambda: _run_fid_check_sync(file_payload, form_params, start_time),
        upload_session_token,
        build_fid_callback_url(),
        log_tag="FID",
    )


def _write_fid_safe_segment(name: str, fallback: str = "fid") -> str:
    """上传目录/文件名片段：保留可读字符，去掉路径非法符号。"""
    s = (name or "").strip() or fallback
    for ch in r'\/:*?"<>|\n\r\t':
        s = s.replace(ch, "_")
    s = s.strip(" .")
    if not s:
        s = fallback
    return s[:200]


@router.post("/api/eld_checked")
async def eld_check(
    background_tasks: BackgroundTasks,
    file: UploadFile | str = File(...),
    company: str = Form(...),
    fab: str = Form(...),
    building: str = Form(...),
    buildingLevel: str = Form(...),
    equipmentList: str = Form(...),
    equipmentGroupList: str = Form(...),
    layerList: str = Form(...),
    gridList: str = Form(...),
    mode: str = Form("default"),
    uploadSessionToken: str = Form(""),
):
    upload_session_token = (uploadSessionToken or "").strip()
    start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(
        "-" * 30
        + f"{datetime.datetime.now()}接收ELD参数 uploadSessionToken={upload_session_token}"
        + "-" * 30
    )

    try:
        file_payload = await _prepare_file_payload(file)
    except Exception as e:
        logger.error(traceback.format_exc())
        return make_task_error_response(f"算法调用失败: {str(e)}", detail=str(e))

    form_params = {
        "company": company,
        "fab": fab,
        "building": building,
        "buildingLevel": buildingLevel,
        "equipmentList": equipmentList,
        "equipmentGroupList": equipmentGroupList,
        "layerList": layerList,
        "gridList": gridList,
        "mode": mode,
        "uploadSessionToken": upload_session_token,
    }
    background_tasks.add_task(
        _eld_check_background,
        file_payload,
        form_params,
        upload_session_token,
        start_time,
    )
    return make_async_accept_response(upload_session_token)

@router.post("/api/fid_checker")
async def fid_check(
    background_tasks: BackgroundTasks,
    file: UploadFile | str = File(...),
    company: str = Form(...),
    fab: str = Form(...),
    building: str = Form(...),
    buildingLevel: str = Form(...),
    system: str = Form(...),
    subsystemList: str = Form(...),
    fieldList: str = Form(...),
    interfaceList: str = Form(...),
    systemInterfaceList: str = Form(...),
    mode: str = Form("default"),
    uploadSessionToken: str = Form(""),
):
    upload_session_token = (uploadSessionToken or "").strip()
    start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(
        "-" * 30
        + f"{datetime.datetime.now()}接收FID参数 uploadSessionToken={upload_session_token}"
        + "-" * 30
    )

    try:
        file_payload = await _prepare_file_payload(file)
    except Exception as e:
        logger.error(traceback.format_exc())
        return make_task_error_response(f"算法调用失败: {str(e)}", detail=str(e))

    form_params = {
        "company": company,
        "fab": fab,
        "building": building,
        "buildingLevel": buildingLevel,
        "system": system,
        "subsystemList": subsystemList,
        "fieldList": fieldList,
        "interfaceList": interfaceList,
        "systemInterfaceList": systemInterfaceList,
        "mode": mode,
        "uploadSessionToken": upload_session_token,
    }
    background_tasks.add_task(
        _fid_check_background,
        file_payload,
        form_params,
        upload_session_token,
        start_time,
    )
    return make_async_accept_response(upload_session_token)


@router.post("/api/write_fid")
async def write_fid(
    body: WriteFidRequest,
):
    """fid 图纸数据回填：默认按 filePath 从 FTP 下载 DXF；若提供 localDxfPath 则读本地文件。结果上传至 EFMS/fid_with_assignment/…，响应 data 为 fid_with_assignment/…"""
    write_fid_logger.info('-' * 30 + f'{datetime.datetime.now()}接收FID图纸数据回填参数' + '-' * 30)
    if not body.filePath.strip():
        return WriteFidResponse(
            code=400,
            message="FID图纸数据回填失败: filePath 不能为空",
            success=False,
            data=""
        ).model_dump(by_alias=True)

    interfaces = [item.model_dump(by_alias=True) for item in body.interfacesDetailList]
    if not interfaces:
        return WriteFidResponse(
            code=400,
            message="FID图纸数据回填失败: interfacesDetailList 不能为空",
            success=False,
            data=""
        ).model_dump(by_alias=True)

    remote_filename = body.filePath.strip()
    local_override = (body.local_dxf_path or "").strip()
    request_dump = body.model_dump(mode="json", by_alias=True)

    def sync_write_fid():
        try:
            t_total = time.perf_counter()
            start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            src_stem = PurePosixPath(remote_filename.replace("\\", "/")).stem
            upload_name = _write_fid_safe_segment(src_stem)
            work_dir = Path(config.UPLOAD_DIR) / upload_name
            work_dir.mkdir(parents=True, exist_ok=True)

            exec_cfg_path = work_dir / f"接收参数-execconfig-{start_time}.json"
            with open(exec_cfg_path, "w", encoding="utf-8") as f:
                json.dump(request_dump, f, ensure_ascii=False, indent=2)

            local_src = work_dir / f"下载图纸-{upload_name}-{start_time}.dxf"
            t_step = time.perf_counter()
            if local_override:
                src_path = Path(local_override).expanduser().resolve()
                if not src_path.is_file():
                    write_fid_logger.warning(
                        f"FID回填中止: 本地DXF不存在, 已耗时 {time.perf_counter() - t_total:.3f}s "
                        f"(path={src_path})"
                    )
                    return WriteFidResponse(
                        code=400,
                        message=f"FID图纸数据回填失败: 本地 DXF 不存在或不是文件 {src_path}",
                        success=False,
                        data=""
                    ).model_dump(by_alias=True)
                shutil.copy2(src_path, local_src)
                write_fid_logger.info(
                    f"FID回填耗时: 复制本地DXF {time.perf_counter() - t_step:.3f}s "
                    f"(path={src_path})"
                )
            else:
                download_file_from_ftp(
                    host=FTP_CONFIG['host'],
                    username=FTP_CONFIG['username'],
                    password=FTP_CONFIG['password'],
                    port=FTP_CONFIG['port'],
                    local_file_path=str(local_src),
                    remote_filename=remote_filename,
                )
                write_fid_logger.info(
                    f"FID回填耗时: FTP下载源图 {time.perf_counter() - t_step:.3f}s "
                    f"(remote={remote_filename})"
                )

            t_step = time.perf_counter()
            try:
                doc = ezdxf.readfile(str(local_src))
            except Exception as read_exc:
                write_fid_logger.warning(
                    f"FID回填中止: 读取DXF失败, 已耗时 {time.perf_counter() - t_total:.3f}s "
                    f"(error={read_exc})"
                )
                return WriteFidResponse(
                    code=400,
                    message=f"FID图纸数据回填失败: 读取DXF失败 {str(read_exc)}",
                    success=False,
                    data=""
                ).model_dump(by_alias=True)
            write_fid_logger.info(f"FID回填耗时: 读取DXF {time.perf_counter() - t_step:.3f}s")

            t_step = time.perf_counter()
            cleared = clear_equ_attributes(doc)
            write_fid_logger.info(
                f"FID回填耗时: 清空EQU属性 {time.perf_counter() - t_step:.3f}s "
                f"(cleared={cleared})"
            )

            t_step = time.perf_counter()
            assigned_count, written = write_equipment_code(doc, interfaces, remote_filename)
            write_fid_logger.info(
                f"FID回填耗时: 写入设备编码 {time.perf_counter() - t_step:.3f}s "
                f"(assigned={assigned_count}, written={written})"
            )

            t_step = time.perf_counter()
            colored_total, colored_assigned = apply_takeoff_colors(doc, interfaces, remote_filename)
            write_fid_logger.info(
                f"FID回填耗时: Takeoff着色 {time.perf_counter() - t_step:.3f}s "
                f"(gray_entities={colored_total}, assigned_inserts={colored_assigned})"
            )

            _, ftp_remote_path, api_data_path = build_write_fid_ftp_result_names(src_stem)
            local_out = work_dir / f"回填图纸-{upload_name}-save-{start_time}.dxf"

            t_step = time.perf_counter()
            doc.saveas(str(local_out))
            write_fid_logger.info(f"FID回填耗时: 保存DXF {time.perf_counter() - t_step:.3f}s (path={local_out})")

            t_step = time.perf_counter()
            upload_file_to_ftp(
                host=FTP_CONFIG['host'],
                username=FTP_CONFIG['username'],
                password=FTP_CONFIG['password'],
                port=FTP_CONFIG['port'],
                local_file_path=str(local_out),
                remote_path=ftp_remote_path,
            )
            write_fid_logger.info(
                f"FID回填耗时: FTP上传结果图 {time.perf_counter() - t_step:.3f}s "
                f"(remote={ftp_remote_path})"
            )

            elapsed_total = time.perf_counter() - t_total
            write_fid_logger.info(
                f"FID回填完成: 总耗时 {elapsed_total:.3f}s, ftp_src={remote_filename}, "
                f"local_work={work_dir}, ftp_dst={ftp_remote_path}, "
                f"interfaces={len(interfaces)}, cleared_equ={cleared}, "
                f"assigned={assigned_count}, written={written}, "
                f"color_default={colored_total}, color_assigned={colored_assigned}"
            )

            return WriteFidResponse(
                code=200,
                message="调用成功",
                success=True,
                data=api_data_path
            ).model_dump(by_alias=True)
        except Exception as e:
            write_fid_logger.exception(
                f"FID回填失败: 总耗时 {time.perf_counter() - t_total:.3f}s, error={e}"
            )
            return WriteFidResponse(
                code=400,
                message=f"FID图纸数据回填失败: {str(e)}",
                success=False,
                data=""
            ).model_dump(by_alias=True)

    t_request = time.perf_counter()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, sync_write_fid)
    write_fid_logger.info(f"FID回填接口耗时(含线程调度): {time.perf_counter() - t_request:.3f}s")
    return result



