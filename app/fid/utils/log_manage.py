import os
import shutil
from pathlib import Path


def get_dir_size(path: Path) -> int:
    """计算目录总大小（字节）"""
    total = 0
    path = Path(path)
    if path.is_dir():
        for entry in path.rglob('*'):
            if entry.is_file():
                total += entry.stat().st_size
    elif path.is_file():
        total += path.stat().st_size
    return total


def cleanup_old_logs(logs_dir: Path, max_size_bytes: int):
    """
    当 logs_dir 总大小超过 max_size_bytes 时，
    按修改时间从旧到新删除子文件夹，直到满足大小限制。
    """

    logs_dir = Path(logs_dir)
    if not logs_dir.exists():
        print(f"{logs_dir}不存在")
        return

    # 获取所有子文件夹（只一级）
    # subdirs = [p for p in logs_dir.iterdir() if p.is_dir()]
    # if not subdirs:
    #     print(f"{subdirs=}不存在子文件夹")
    #     return
    subdirs = [p for p in logs_dir.iterdir()]

    # 按最后修改时间排序（最早在前）
    subdirs.sort(key=lambda x: x.stat().st_mtime)

    current_size = get_dir_size(logs_dir)
    print(f"{current_size=}")
    if current_size <= max_size_bytes:
        print(f"current_size({current_size / (1024 ** 3):.4f} GB) < max_size_bytes({max_size_bytes / (1024 ** 3):.4f} GB)")
        return  # 未超限，无需清理

    print(
        f"Logs size {current_size / (1024 ** 3):.4f} GB exceeds limit {max_size_bytes / (1024 ** 3):.4f} GB. Cleaning up...")

    for oldest_dir in subdirs:
        try:
            dir_size = get_dir_size(oldest_dir)
            if Path(oldest_dir).is_dir():
                shutil.rmtree(oldest_dir, ignore_errors=True)
            elif Path(oldest_dir).is_file():
                Path(oldest_dir).unlink(missing_ok=True)
            print(f"删除{oldest_dir}")
            current_size -= dir_size
            print(f"Deleted old log folder: {oldest_dir} ({dir_size / (1024 ** 2):.4f} MB)")

            if current_size <= max_size_bytes:
                break
        except Exception as e:
            print(f"Failed to delete {oldest_dir}: {e}")

if __name__ == '__main__':
    logs_dir = '/data/new_merge_interface/app/fid/temp_uploads'
    cleanup_old_logs(logs_dir, max_size_bytes=1024**2)
