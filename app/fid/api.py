#/app/fid/api.py
import datetime
import json
import subprocess
import sys
import traceback
import asyncio

import re
from pathlib import Path

from fastapi import File, Form, UploadFile, APIRouter

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

from app.config import logger, fid_config as config
from app.fid.utils.log_manage import cleanup_old_logs
#from app.config.fid_config import FTP_CONFIG
from app.fid.utils.ftp_download import download_file_from_ftp

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
from app.config.fid_config import FTP_CONFIG

router = APIRouter()


@router.post("/api/eld_checked")
async def eld_check(
    file: UploadFile | str = File(...),
    company: str = Form(...),
    fab: str = Form(...),
    building: str = Form(...),
    buildingLevel: str = Form(...),
    equipmentList: str = Form(...),  # 必须是字符串
    equipmentGroupList: str = Form(...),
    layerList: str = Form(...),
    gridList: str = Form(...),
    mode: str = Form("default"),
):
    try:
        # result = await _eld_check(file, company, fab, building, buildingLevel, equipmentList,
        #                    equipmentGroupList, layerList, gridList)
        logger.info('-' * 30 + f'{datetime.datetime.now()}接收ELD参数' + '-' * 30)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            if not isinstance(file, str):
                filename = re.sub('[^a-zA-Z0-9]', '', Path(file.filename).stem)
                work_dir = Path(config.UPLOAD_DIR) / f"eld_{filename}"
                work_dir.mkdir(parents=True, exist_ok=True)

                file_path = work_dir / f"{Path(file.filename).stem}_{start_time}.dxf"
                with open(file_path, 'wb') as f:
                    file_content = await file.read()
                    f.write(file_content)
                file_path = file_path.absolute()
            else:
                filename = re.sub('[^a-zA-Z0-9]', '', Path(file).stem)
                work_dir = Path(config.UPLOAD_DIR) / f"eld_{filename}"
                file_path = work_dir / f"{Path(file).stem}_{start_time}.dxf"
                work_dir.mkdir(parents=True, exist_ok=True)

                download_file_from_ftp(
                    host=FTP_CONFIG['host'],
                    username=FTP_CONFIG['username'],
                    password=FTP_CONFIG['password'],
                    port=FTP_CONFIG['port'],
                    local_file_path=str(file_path),
                    remote_filename=file
                )
        except Exception as save_dxf_exception:
            raise Exception(f'dxf文件保存遇到错误： {str(save_dxf_exception)}')

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        #log_file = Path("./logs") / f"eld_{Path(file.filename).stem}" /f"{timestamp}.log"



        exec_config_path = work_dir / f'exec_config_{start_time}.json'
        log_file = exec_config_path.parent / f"{timestamp}.log"

        exec_config_path.parent.mkdir(parents=True, exist_ok=True)

        config_json = {
            'file_path': str(file_path),
            'company': json.loads(company),
            'fab': json.loads(fab),
            'building': json.loads(building),
            'buildingLevel': json.loads(buildingLevel),
            'equipmentList':json.loads(equipmentList),
            'equipmentGroupList':json.loads(equipmentGroupList),
            'layerList':json.loads(layerList),
            'gridList':json.loads(gridList),
            'mode': mode,
            'mission_start_time': start_time
        }
        with open(exec_config_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(config_json, ensure_ascii=False, indent=4))

        # --- 同步子进程函数（将被 run_in_executor 调用）---
        def run_subprocess_sync():
            cmd = [
                sys.executable, "-u",
                str(Path(__file__).parent / "eld_check_cli.py"),
                str(exec_config_path.absolute())
            ]
            with open(log_file, "w", encoding="utf-8") as log_f:
                result = subprocess.run(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            return result.returncode

        loop = asyncio.get_event_loop()
        returncode = await loop.run_in_executor(None, run_subprocess_sync)

        if returncode == 0:
            try:
                with open(Path(exec_config_path).parent / f'result_{start_time}.json', 'r', encoding='utf-8') as f:
                    result = json.load(f)
                return result
            except json.JSONDecodeError:
                raise RuntimeError("子进程返回非JSON结果")
        else:
            raise RuntimeError(f"子进程执行失败，日志: {log_file}")

    except Exception as e:
        return {
            "code": 400,
            "message": f"算法调用失败: {str(e)}"
        }

@router.post("/api/fid_checker")
async def fid_check(
        file: UploadFile | str = Form(...),
        company: str = Form(...),
        fab: str = Form(...),
        building: str = Form(...),
        buildingLevel: str = Form(...),
        system: str = Form(...),  # 必须是字符串
        subsystemList: str = Form(...),
        fieldList: str = Form(...),
        interfaceList: str = Form(...),
        systemInterfaceList: str = Form(...),
        mode: str = Form("default"),
):
    try:
        logger.info('-' * 30 + f'{datetime.datetime.now()}接收FID参数' + '-' * 30)
        start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            if not isinstance(file, str):
                filename = re.sub('[^a-zA-Z0-9]', '', Path(file.filename).stem)
                work_dir = Path(config.UPLOAD_DIR) / f"fid_{filename}"
                work_dir.mkdir(parents=True, exist_ok=True)
                file_path = work_dir / f"{Path(file.filename).stem}_{start_time}.dxf"
                with open(file_path, 'wb') as f:
                    file_content = await file.read()
                    f.write(file_content)
                file_path = file_path.absolute()
            else:
                filename = re.sub('[^a-zA-Z0-9]', '', Path(file).stem)
                work_dir = Path(config.UPLOAD_DIR) / f"fid_{filename}"
                file_path = work_dir / f"{Path(file).stem}_{start_time}.dxf"
                work_dir.mkdir(parents=True, exist_ok=True)
                download_file_from_ftp(
                    host=FTP_CONFIG['host'],
                    username=FTP_CONFIG['username'],
                    password=FTP_CONFIG['password'],
                    port=FTP_CONFIG['port'],
                    local_file_path=str(file_path),
                    remote_filename=file
                )
        except Exception as save_dxf_exception:
            raise Exception(f'dxf文件保存遇到错误： {str(save_dxf_exception)}')

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        #log_file = Path("./logs") / f"fid_{Path(file.filename).stem}" /f"{timestamp}.log"

        # separator = "-" * 20  # 定义分割线长度

        # with open(work_dir / f'rec_config_{start_time}.txt', 'w', encoding='utf-8') as f:
        #     # 辅助函数：写入标签、值和分割线
        #     def write_field(label, value):
        #         f.write(f"{label}: {value}\n")
        #         f.write(f"{separator}\n")

        #     write_field("File", file)
        #     write_field("Company", company)
        #     write_field("Fab", fab)
        #     write_field("Building", building)
        #     write_field("Building Level", buildingLevel)
        #     write_field("System", system)
        #     write_field("Subsystem List", subsystemList)
        #     write_field("Field List", fieldList)
        #     write_field("Interface List", interfaceList)
        #     write_field("System Interface List", systemInterfaceList)

        #     f.write("End of Config\n")  # 结束标记

        exec_config_path = work_dir / f'exec_config_{start_time}.json'
        log_file = exec_config_path.parent / f"{timestamp}.log"

        exec_config_path.parent.mkdir(parents=True, exist_ok=True)

        config_json = {
            'file_path': str(file_path),
            'company': json.loads(company),
            'fab': json.loads(fab),
            'building': json.loads(building),
            'buildingLevel': json.loads(buildingLevel),
            'system':json.loads(system),
            'subsystemList':json.loads(subsystemList),
            'fieldList':json.loads(fieldList),
            'interfaceList':json.loads(interfaceList),
            'systemInterfaceList':json.loads(systemInterfaceList),
            'mode': mode,
            'mission_start_time': start_time
        }
        with open(exec_config_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(config_json, ensure_ascii=False, indent=4))

        # --- 同步子进程函数（将被 run_in_executor 调用）---
        def run_subprocess_sync():
            cmd = [
                sys.executable, "-u",
                str(Path(__file__).parent / "fid_check_cli.py"),
                str(exec_config_path.absolute())
            ]
            with open(log_file, "w", encoding="utf-8") as log_f:
                result = subprocess.run(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            return result.returncode

        # --- 异步执行同步函数 ---
        loop = asyncio.get_event_loop()
        returncode = await loop.run_in_executor(None, run_subprocess_sync)

        if returncode == 0:
            try:
                with open(Path(exec_config_path).parent / f'result_{start_time}.json', 'r', encoding='utf-8') as f:
                    result = json.load(f)

                cleanup_old_logs(config.UPLOAD_DIR, config.MEMORY_LIMIT)
                return result
            except json.JSONDecodeError:
                raise RuntimeError("子进程返回非JSON结果")
        else:
            raise RuntimeError(f"子进程执行失败，日志: {log_file}")

    except Exception as e:
        return {
            "code": 400,
            "message": f"算法调用失败: {str(e)}"
        }




