#app/config/fid_config.py
import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv

# 1. 加载 .env 文件
# 假设 .env 在当前文件所在目录或项目根目录
current_file = Path(__file__).resolve()
current_dir = current_file.parent.parent.parent

# 2. 构建 .env 的路径
# 情况 A: .env 就在当前文件同级目录
env_path = current_dir / 'global_config/env'

print(f"{env_path=}")
is_loaded = load_dotenv(dotenv_path=env_path, verbose=True, override=True)
print(f"{is_loaded=}")

def get_list_from_env(key: str, default: list) -> list:
    """辅助函数：从环境变量获取列表，支持逗号分隔的字符串"""
    val = os.getenv(key)
    if not val:
        return default
    # 去除空格并分割
    return [item.strip() for item in val.split(',') if item.strip()]

def get_int_from_env(key: str, default: int) -> int:
    """辅助函数：从环境变量获取整数"""
    val = os.getenv(key)
    return int(val) if val else default



# 必填字段和 TOOL_ID 正则保持不变
#REQUIRED_FIELDS = ["tool_id", "owner", "vendor", "model"]
REQUIRED_FIELDS = ["tool_id", 'owner']
TOOL_ID_PATTERN = r'^[A-Z].*\d{2}$'


#FID检验
FID_REQUIRED_FIELDS = {
    'TAKEOFF':["INTERFACE_CODE", "CS", "CT"],
    'VMB_CHEMICAL':["ID", "CHEMICALNAME", "CT.", "CS."], #"I/O."
    'VMB_GASNAME':["ID", "GASNAME", "CT.", "CS."],
    'I_LINE':["ID_SHORT", "ID"],
    'GPB':["ID_SHORT", "ID", "CS."], #固定式工艺盘
    'NEW_INTER_':["ID_SHORT", "ID", "CS"],
}

from pathlib import Path

# 获取当前文件所在目录，向上追溯到项目根目录
# 假设当前文件在 project/app/core/config.py
current_file = Path(__file__).resolve()  # /project/app/core/config.py
project_root = current_file.parent.parent.parent

# 构建目标路径
relative_path = os.getenv('UPLOAD_DIR_RELATIVE', 'app/fid/temp_uploads')
absolute_path = (project_root / relative_path).resolve()

UPLOAD_DIR = absolute_path

#MEMORY_LIMIT = 40*1024*1024*1024
MEMORY_LIMIT = get_int_from_env('MEMORY_LIMIT', 40) * 1024 * 1024 * 1024

# 6. FTP 配置 (从环境变量构建，避免硬编码密码；变量名 FTP_HOST / FTP_USER / FTP_PASS / FTP_PORT)

disabled_fab_str = os.getenv("DISABLE_FAB", "")
DISABLED_FAB_TUPLE = tuple(item.strip() for item in disabled_fab_str.split(',') if item.strip())


def build_ftp_config(env_prefix: str) -> dict:
    """根据前缀构建 FTP 配置字典"""
    return {
        'host': os.getenv(f'{env_prefix}_HOST'),
        'username': os.getenv(f'{env_prefix}_USER'),
        'password': os.getenv(f'{env_prefix}_PASS'),
        'port': int(os.getenv(f'{env_prefix}_PORT', 21))
    }

FTP_CONFIG = build_ftp_config('FTP')

# 打印调试信息 (生产环境请关闭)
if __name__ == "__main__":
    print(f"Upload Dir: {UPLOAD_DIR}")
    print(f"Required Fields: {REQUIRED_FIELDS}")
    print(f"FTP Host: {FTP_CONFIG['host']}")
    print(f"MEMORY_LIMIT : {MEMORY_LIMIT}")
    print(f"DISABLED_FAB_TUPLE : {DISABLED_FAB_TUPLE}")
    # 不要打印密码
    # print(f"FTP Pass: {FTP_CONFIG['password']}")
