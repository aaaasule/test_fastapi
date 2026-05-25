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
                    logger.warning(
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
                logger.info(
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
                logger.info(
                    f"FID回填耗时: FTP下载源图 {time.perf_counter() - t_step:.3f}s "
                    f"(remote={remote_filename})"
                )

            t_step = time.perf_counter()
            try:
                doc = ezdxf.readfile(str(local_src))
            except Exception as read_exc:
                logger.warning(
                    f"FID回填中止: 读取DXF失败, 已耗时 {time.perf_counter() - t_total:.3f}s "
                    f"(error={read_exc})"
                )
                return WriteFidResponse(
                    code=400,
                    message=f"FID图纸数据回填失败: 读取DXF失败 {str(read_exc)}",
                    success=False,
                    data=""
                ).model_dump(by_alias=True)
            logger.info(f"FID回填耗时: 读取DXF {time.perf_counter() - t_step:.3f}s")

            t_step = time.perf_counter()
            cleared = clear_equ_attributes(doc)
            logger.info(
                f"FID回填耗时: 清空EQU属性 {time.perf_counter() - t_step:.3f}s "
                f"(cleared={cleared})"
            )

            t_step = time.perf_counter()
            assigned_count, written = write_equipment_code(doc, interfaces, remote_filename)
            logger.info(
                f"FID回填耗时: 写入设备编码 {time.perf_counter() - t_step:.3f}s "
                f"(assigned={assigned_count}, written={written})"
            )

            t_step = time.perf_counter()
            colored_total, colored_assigned = apply_takeoff_colors(doc, interfaces, remote_filename)
            logger.info(
                f"FID回填耗时: Takeoff着色 {time.perf_counter() - t_step:.3f}s "
                f"(gray_entities={colored_total}, assigned_inserts={colored_assigned})"
            )

            _, ftp_remote_path, api_data_path = build_write_fid_ftp_result_names(src_stem)
            local_out = work_dir / f"回填图纸-{upload_name}-save-{start_time}.dxf"

            t_step = time.perf_counter()
            doc.saveas(str(local_out))
            logger.info(f"FID回填耗时: 保存DXF {time.perf_counter() - t_step:.3f}s (path={local_out})")

            t_step = time.perf_counter()
            upload_file_to_ftp(
                host=FTP_CONFIG['host'],
                username=FTP_CONFIG['username'],
                password=FTP_CONFIG['password'],
                port=FTP_CONFIG['port'],
                local_file_path=str(local_out),
                remote_path=ftp_remote_path,
            )
            logger.info(
                f"FID回填耗时: FTP上传结果图 {time.perf_counter() - t_step:.3f}s "
                f"(remote={ftp_remote_path})"
            )

            elapsed_total = time.perf_counter() - t_total
            logger.info(
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
            logger.exception(
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
    logger.info(f"FID回填接口耗时(含线程调度): {time.perf_counter() - t_request:.3f}s")
    return result
