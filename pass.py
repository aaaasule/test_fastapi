# -*- coding: utf-8 -*-
"""SLD 校验 HTTP 接口：保存 DXF、写 exec_config、子进程执行 cli、读结果。"""
from __future__ import annotations

import asyncio
import datetime
import json
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from fastapi import APIRouter

from app.config import logger
from app.config.fid_config import FTP_CONFIG
from app.fid.utils.ftp_download import download_file_from_ftp
from app.sld.schemas import SldCheckRequest

router = APIRouter()

# 本模块内所有文件读写（工作目录、本地 DXF）均限定在 app/sld 下
SLD_DIR = Path(__file__).resolve().parent
# ``local:`` 前缀表示 app/sld 下本地路径；无前缀一律按 FTP 远端路径下载
LOCAL_FILE_PREFIX = "local:"


def _is_path_under(base: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _api_error(message: str, *, detail: str | None = None) -> dict:
    errs = [detail] if detail else [message]
    return {
        "code": 400,
        "message": message,
        "success": False,
        "data": [{"errors": errs}],
    }


def _resolve_local_under_sld(local_path: str) -> Path | dict:
    """解析 ``local:`` 后的路径，须落在 ``app/sld`` 下且为已存在文件。"""
    raw = local_path.strip()
    if not raw:
        return _api_error("local: 后路径不能为空", detail="local: 后路径不能为空")

    sld_root = SLD_DIR.resolve()
    exp = Path(raw).expanduser()
    if exp.is_absolute():
        candidate = exp.resolve()
        if not _is_path_under(sld_root, candidate):
            return _api_error(
                "本地 file 必须在 app/sld 目录下",
                detail=f"拒绝访问: {candidate}",
            )
    else:
        candidate = (SLD_DIR / exp).resolve()
        if not _is_path_under(sld_root, candidate):
            return _api_error(
                "file 相对路径解析后须位于 app/sld 目录下",
                detail=f"路径越界: {raw}",
            )

    if not candidate.is_file():
        return _api_error(
            "本地 DXF 不存在或不是文件",
            detail=str(candidate),
        )
    return candidate


def _stem_for_work_dir(file_ref: str) -> str:
    path_str = file_ref
    if file_ref.startswith(LOCAL_FILE_PREFIX):
        path_str = file_ref[len(LOCAL_FILE_PREFIX) :].strip()
    return Path(path_str.replace("\\", "/")).stem


@router.post("/api/sld_check")
async def sld_check(body: SldCheckRequest) -> dict:
    """
    SLD 校验：JSON Body，字段与《SLD和FID回填》「SLD校验」一致。

    ``file`` 约定：
    - ``local:<path>``：``app/sld`` 下本地 DXF（``path`` 相对 ``app/sld`` 或绝对路径但须在目录内）；
    - 其它值：FTP 远端路径（原样 ``RETR``，可含 ``/`` 多级目录）。
    """
    try:
        logger.info("-" * 30 + f"{datetime.datetime.now()}接收SLD参数(JSON)" + "-" * 30)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        file_ref = (body.file or "").strip()
        if not file_ref:
            return _api_error("file 不能为空", detail="file 不能为空")

        use_local = file_ref.startswith(LOCAL_FILE_PREFIX)
        stem = _stem_for_work_dir(file_ref)
        filename = re.sub("[^a-zA-Z0-9]", "", stem)
        work_dir = SLD_DIR / "work" / f"sld_{filename}"
        work_dir.mkdir(parents=True, exist_ok=True)
        file_path = work_dir / f"{stem}_{start_time}.dxf"

        try:
            if use_local:
                local_path = file_ref[len(LOCAL_FILE_PREFIX) :]
                resolved = _resolve_local_under_sld(local_path)
                if isinstance(resolved, dict):
                    return resolved
                shutil.copy2(resolved, file_path)
                file_path = file_path.resolve()
            else:
                file_path = file_path.resolve()
                download_file_from_ftp(
                    host=FTP_CONFIG["host"],
                    username=FTP_CONFIG["username"],
                    password=FTP_CONFIG["password"],
                    port=FTP_CONFIG["port"],
                    local_file_path=str(file_path),
                    remote_filename=file_ref,
                )
        except Exception as save_exc:
            raise Exception(f"DXF文件保存遇到错误：{str(save_exc)}") from save_exc

        exec_config_path = work_dir / f"exec_config_{start_time}.json"
        log_file = exec_config_path.parent / f"{start_time}.log"

        config_json = {
            "file_path": str(file_path),
            "company": body.company,
            "fab": body.fab,
            "building": body.building,
            "buildingLevel": body.buildingLevel,
            "equipmentList": body.equipmentList,
            "eldSubEquipmentList": body.eldSubEquipmentList,
            "layerList": body.layerList,
            "gridList": body.gridList,
            "mission_start_time": start_time,
        }
        exec_config_path.parent.mkdir(parents=True, exist_ok=True)
        exec_config_path.write_text(
            json.dumps(config_json, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )

        def run_subprocess_sync() -> int:
            cmd = [sys.executable, "-u", "-m", "app.sld.cli", str(exec_config_path.absolute())]
            with open(log_file, "w", encoding="utf-8") as log_f:
                result = subprocess.run(cmd, stdout=log_f, stderr=subprocess.STDOUT, text=True)
            return result.returncode

        loop = asyncio.get_event_loop()
        returncode = await loop.run_in_executor(None, run_subprocess_sync)

        result_path = Path(exec_config_path).parent / f"result_{start_time}.json"
        if result_path.is_file():
            with open(result_path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "code": 400,
            "message": f"子进程未生成结果(returncode={returncode})，日志: {log_file}",
            "success": False,
            "data": [{"errors": [f"子进程 returncode={returncode}"]}],
        }

    except Exception as e:
        logger.error(traceback.format_exc())
        return _api_error(f"算法调用失败: {str(e)}", detail=str(e))
