@router.post("/api/write_fid")
async def write_fid(
    body: WriteFidRequest,
):
    """fid 图纸数据回填：默认按 filePath 从 FTP 下载 DXF；若提供 localDxfPath 则读本地文件。结果上传至 EFMS/fid_with_assignment/…，响应 data 为 fid_with_assignment/…"""
    logger.info('-' * 30 + f'{datetime.datetime.now()}接收FID图纸数据回填参数' + '-' * 30)
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
            start_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            src_stem = PurePosixPath(remote_filename.replace("\\", "/")).stem
            upload_name = _write_fid_safe_segment(src_stem)
            work_dir = Path(config.UPLOAD_DIR) / upload_name
            work_dir.mkdir(parents=True, exist_ok=True)

            exec_cfg_path = work_dir / f"接收参数-execconfig-{start_time}.json"
            with open(exec_cfg_path, "w", encoding="utf-8") as f:
                json.dump(request_dump, f, ensure_ascii=False, indent=2)

            local_src = work_dir / f"下载图纸-{upload_name}-{start_time}.dxf"
            if local_override:
                src_path = Path(local_override).expanduser().resolve()
                if not src_path.is_file():
                    return WriteFidResponse(
                        code=400,
                        message=f"FID图纸数据回填失败: 本地 DXF 不存在或不是文件 {src_path}",
                        success=False,
                        data=""
                    ).model_dump(by_alias=True)
                shutil.copy2(src_path, local_src)
            else:
                download_file_from_ftp(
                    host=FTP_CONFIG['host'],
                    username=FTP_CONFIG['username'],
                    password=FTP_CONFIG['password'],
                    port=FTP_CONFIG['port'],
                    local_file_path=str(local_src),
                    remote_filename=remote_filename,
                )

            try:
                doc = ezdxf.readfile(str(local_src))
            except Exception as read_exc:
                return WriteFidResponse(
                    code=400,
                    message=f"FID图纸数据回填失败: 读取DXF失败 {str(read_exc)}",
                    success=False,
                    data=""
                ).model_dump(by_alias=True)

            cleared = clear_equ_attributes(doc)
            assigned_count, written = write_equipment_code(doc, interfaces, remote_filename)
            colored_total, colored_assigned = apply_takeoff_colors(doc, interfaces, remote_filename)

            _, ftp_remote_path, api_data_path = build_write_fid_ftp_result_names(src_stem)
            local_out = work_dir / f"回填图纸-{upload_name}-save-{start_time}.dxf"
            doc.saveas(str(local_out))

            upload_file_to_ftp(
                host=FTP_CONFIG['host'],
                username=FTP_CONFIG['username'],
                password=FTP_CONFIG['password'],
                port=FTP_CONFIG['port'],
                local_file_path=str(local_out),
                remote_path=ftp_remote_path,
            )

            logger.info(
                f"FID回填完成: ftp_src={remote_filename}, local_work={work_dir}, "
                f"ftp_dst={ftp_remote_path}, cleared_equ={cleared}, assigned={assigned_count}, "
                f"written={written}, color_default={colored_total}, color_assigned={colored_assigned}"
            )

            return WriteFidResponse(
                code=200,
                message="调用成功",
                success=True,
                data=api_data_path
            ).model_dump(by_alias=True)
        except Exception as e:
            return WriteFidResponse(
                code=400,
                message=f"FID图纸数据回填失败: {str(e)}",
                success=False,
                data=""
            ).model_dump(by_alias=True)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_write_fid)
