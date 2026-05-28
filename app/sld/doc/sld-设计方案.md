# SLD 校验模块 — 设计方案摘要

## 1. 目标

在 `app/sld/` 下实现与 **FID/ELD 代码解耦** 的 SLD 图纸（DXF）校验：解析、规范性校验、柱网匹配、变更对比，并通过 HTTP 接口返回统一 JSON。

## 2. 目录与职责

| 文件 | 职责 |
|------|------|
| [api.py](api.py) | FastAPI：`POST /api/sld_check`，保存 DXF、写 `exec_config.json`、子进程执行、读 `result_*.json` |
| [cli.py](cli.py) | 子进程入口：`python -m app.sld.cli <exec_config.json>` |
| [checker.py](checker.py) | 主流程编排：`run_sld_check` |
| [parser.py](parser.py) | DXF 解析：`parse_sld_dxf` → `List[SldDevice]` |
| [grid.py](grid.py) | 柱网：`SldGridMatcher`（KD 树批量查询，独立于 fid） |
| [models.py](models.py) | `SldDevice`、`SldIssue`、`SldFileContext` |
| [constants.py](constants.py) | `ID_EQU_PATTERN`、位置阈值、`DEFAULT_BBOX_FAST` |
| [validators/spec.py](validators/spec.py) | 文件名、ID_EQU 格式、唯一性、必填、OWNER 编组 |
| [validators/change.py](validators/change.py) | 新增/删除/属性变更/位置变更 |
| [validators/grouping.py](validators/grouping.py) | 问题聚合为 API `items` 列表 |
| [schemas.py](schemas.py) | Pydantic 文档化结构（可选） |

## 3. 接口约定

- **路径**：`POST /api/sld_check`
- **表单**：`file`, `company`, `fab`, `building`, `buildingLevel`, `equipmentList`, `equipmentGroupList`, `layerList`, `gridList`（与 ELD 类似，均为 JSON 字符串字段除 `file` 外）
- **成功体**：`{ code, message, success, data: { error, warning, eqp_data } }`
- **业务主键**：`ID_EQU` + `ID_EquSubShort`；图元过滤依赖 **`ID_EQU` 或 `ID_EquSubShort`** 任一非空（见 [doc/sld_check.md](doc/sld_check.md)）

## 4. 基础设施说明

- **上传目录与 FTP**：与现有工程一致，复用 `app.config.fid_config` 中的 `UPLOAD_DIR`、`FTP_CONFIG` 及 `app.fid.utils.ftp_download.download_file_from_ftp`，避免重复配置；**校验算法本身不依赖 `app.fid` 校验器或解析器**。

## 5. 大图纸性能要点

1. **解析**：仅对含 `ID_EQU` 或 `ID_EquSubShort` 的 INSERT 计算包围盒；`bbox.extents(..., fast=DEFAULT_BBOX_FAST)` 默认快速模式。  
2. **柱网**：`cKDTree` 一次构建，对所有设备中心点 **批量** `query`。  
3. **校验**：唯一性、变更等用 **字典/集合** 聚合键，避免 O(n²) 双重循环。  
4. **缓存**：解析结果写入 `cache_folder/parser_{mission_start_time}.json` 便于排障。

## 6. 与需求文档对应关系

详见 [doc/sld_check.md](doc/sld_check.md)（解析字段、错误类型、返回 JSON 顶层结构）。
