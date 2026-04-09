#/app/fid/eld_check_cli.py
import sys
import json
import traceback
from pathlib import Path

# 将 eld_validator 目录（即 fid 的父目录）加入 sys.path
PARENT_DIR = Path(__file__).parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from api_util import _eld_check, _fid_check
import asyncio


def main():
    try:

        config_path = sys.argv[1]
        print(f"{config_path=}")
        with open(config_path, 'r', encoding='utf-8') as f:
            params = json.load(f)

        #print(f"{params=}")
        # 调用核心逻辑（需改造 _eld_check）
        #result = _fid_check(**params)
        params['cache_folder'] = str(Path(config_path).parent)
        result = asyncio.run(_eld_check(**params))

        # 输出 JSON 到 stdout（供父进程读取）
        #print(json.dumps(result, ensure_ascii=False))

        with open(Path(config_path).parent / f"result_{params['mission_start_time']}.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    except Exception as e:
        print(traceback.format_exc())
        error_result = {
            "code": 400,
            "message": f"算法调用失败: {str(e)}",
            "traceback": traceback.format_exc()
        }
        with open(Path(config_path).parent / f"result_{params['mission_start_time']}.json", 'w', encoding='utf-8') as f:
            f.write(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
