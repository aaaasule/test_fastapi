from ftplib import FTP, error_perm
import os
import traceback


def upload_file_to_ftp(
        host: str,
        username: str,
        password: str,
        port: int,
        local_file_path: str,
        remote_path: str,
):
    """
    上传本地文件到 FTP。
    remote_path: 相对于 FTP 登录后起始目录的路径，使用 posix 分隔符，且无 leading slash，
        例如 ``fid_with_assignment/foo_20260101120000.dxf``。
    会自动逐级创建远端目录（若权限允许）。
    """
    remote_path = remote_path.replace("\\", "/").strip("/")
    parts = [p for p in remote_path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("remote_path 须至少包含一级目录和文件名，例如 fid_with_assignment/out.dxf")

    *dir_parts, filename = parts
    ftp = FTP()
    try:
        ftp.connect(host, port)
        ftp.login(username, password)
        ftp.encoding = "utf-8"

        for d in dir_parts:
            try:
                ftp.mkd(d)
            except error_perm:
                pass
            ftp.cwd(d)

        with open(local_file_path, "rb") as f:
            ftp.storbinary(f"STOR {filename}", f)
        ftp.quit()
        return True
    except Exception:
        try:
            ftp.quit()
        except Exception:
            pass
        raise


def download_file_from_ftp(
        host: str,
        username: str,
        password: str,
        port: int,
        local_file_path: str,  # 本地保存路径（如 './report.xlsx'）
        remote_filename: str
):
    """
    从 FTP 服务器下载文件
    """
    try:
        # 创建本地目录（如果不存在）
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        # 连接 FTP
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(username, password)
        ftp.encoding = 'utf-8'  # 支持中文文件名

        print(f"✅ 已连接到 FTP: {host}")
        print(f"{remote_filename=}")

        # # 下载文件
        with open(local_file_path, 'wb') as f:
            ftp.retrbinary(f'RETR {remote_filename}', f.write)

        print(f"📥 下载成功: {local_file_path}")
        ftp.quit()
        return True

    except Exception as e:
        print(traceback.format_exc())
        raise Exception(f"❌ FTP 下载失败: {e}")
        # return False


# 使用示例
if __name__ == "__main__":
    download_file_from_ftp(
        host="10.22.13.66",
        username="BPMadmin",
        password="Aa123456",
        port=21,
        local_file_path='/data/new_merge_interface/app/fid/temp_uploads/YMTC^FID.ES^WS^F2.dxf',
        # remote_filename='/home/devadmin/bs/bpmapp/attachFtp/YMTC/Fab1/_System/PS/_Temp/YMTC^FID.PS^FAB1^F2.dxf'
        # remote_filename='\home\devadmin\YMTC\Fab1\_Equipment\_Layout\_Archive\YMTC^ELD^WS^F1_20260306134218.dxf'
        remote_filename='bs/bpmapp/attachFtp/YMTC/Fab2/_System/ES/_Temp/YMTC^FID.ES^WS^F2.dxf'
    )
