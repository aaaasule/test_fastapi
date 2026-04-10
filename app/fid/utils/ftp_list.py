"""FTP文件列表获取工具"""
import os
from ftplib import FTP
from typing import List


def list_files_from_ftp2(
        host: str,
        username: str,
        password: str,
        port: int,
        remote_folder: str
) -> List[str]:
    """获取FTP文件夹下的所有文件列表"""
    files = []

    try:
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(username, password)

        try:
            ftp.cwd(remote_folder)
        except Exception as e:
            print(f"无法切换到文件夹 {remote_folder}: {e}")
            ftp.quit()
            return files

        ftp.retrlines('LIST', files.append)
        ftp.quit()

        file_names = []
        for file_info in files:
            parts = file_info.split()
            if len(parts) >= 9:
                filename = ' '.join(parts[8:])
                if not file_info.startswith('d'):
                    file_names.append(os.path.join(remote_folder, filename).replace('\\', '/'))

        return file_names

    except Exception as e:
        print(f"FTP连接失败: {e}")
        return files


#def list_all_dxf_files_recursive(
def list_files_from_ftp(
        host: str,
        username: str,
        password: str,
        port: int,
        remote_folder: str
) -> List[str]:
    """
    递归获取FTP文件夹及所有子目录下的所有DXF文件

    参数：
        host: FTP服务器地址
        username: FTP用户名
        password: FTP密码
        port: FTP端口
        remote_folder: 远程文件夹路径

    返回：
        所有DXF文件路径列表
    """
    dxf_files = []

    try:
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(username, password)

        def recursive_list(folder: str):
            """递归遍历目录"""
            try:
                # 切换到目标文件夹
                ftp.cwd(folder)
            except Exception as e:
                print(f"无法切换到文件夹 {folder}: {e}")
                return

            # 获取当前目录的文件和子目录列表
            items = []
            ftp.retrlines('LIST', items.append)

            for item in items:
                parts = item.split()
                if len(parts) < 9:
                    continue

                name = ' '.join(parts[8:])
                full_path = os.path.join(folder, name).replace('\\', '/')

                # 判断是文件还是目录
                if item.startswith('d'):
                    # 目录：递归进入
                    # 跳过 . 和 ..
                    if name not in ['.', '..']:
                        print(f"📂 进入子目录: {full_path}")
                        recursive_list(full_path)
                else:
                    # 文件：检查是否是DXF文件
                    if name.lower().endswith('.dxf'):
                        dxf_files.append(full_path)
                        print(f"  ✅ 找到DXF: {name}")

        # 开始递归遍历
        recursive_list(remote_folder)

        ftp.quit()

    except Exception as e:
        print(f"FTP连接失败: {e}")

    return dxf_files


def list_dxf_files_from_ftp2(
        host: str,
        username: str,
        password: str,
        port: int,
        remote_folder: str
) -> List[str]:
    """获取FTP文件夹下的所有DXF文件列表（非递归）"""
    all_files = list_files_from_ftp2(host, username, password, port, remote_folder)
    dxf_files = [f for f in all_files if f.lower().endswith('.dxf')]
    return dxf_files


