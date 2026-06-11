import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

_shared_file_handler: "HourlyDateFolderHandler | None" = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_env() -> None:
    env_path = _project_root() / "global_config" / "env"
    load_dotenv(dotenv_path=env_path, override=True)


def _parse_int_env(key: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        value = default
    else:
        value = int(raw.strip())
    if minimum is not None:
        value = max(minimum, value)
    return value


def _parse_float_env(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    return float(raw.strip())


def _resolve_log_path(path_raw: str, project_root: Path) -> Path:
    """
    解析日志根路径：
    - 绝对路径（如 /var/log/fastapi）直接使用，可位于项目目录外
    - 支持 ~ 展开（如 ~/logs/fastapi）
    - 相对路径则相对于项目根目录（如 logs、../shared_logs）
    """
    expanded = Path(os.path.expanduser(path_raw.strip()))
    if expanded.is_absolute():
        return expanded.resolve()
    return (project_root / expanded).resolve()


@dataclass(frozen=True)
class LogSettings:
    log_root: Path
    retention_days: int
    file_name_template: str
    files_per_day: int
    max_size_bytes: int
    backup_count: int


def get_log_settings() -> LogSettings:
    """从 env 读取日志路径、文件名、文件个数、大小与保留策略。"""
    _load_env()
    root = _project_root()

    path_raw = os.getenv("LOG_PATH") or os.getenv("LOG_RETENTION_PATH") or "logs"
    log_root = _resolve_log_path(path_raw, root)

    retention_days = _parse_int_env("LOG_RETENTION_DAYS", 30, minimum=0)
    file_name_template = os.getenv("LOG_FILE_NAME", "{slot:02d}.log").strip() or "{slot:02d}.log"
    files_per_day = _parse_int_env("LOG_FILES_PER_DAY", 24, minimum=1)
    files_per_day = min(files_per_day, 24)

    max_size_mb = _parse_float_env("LOG_FILE_MAX_SIZE_MB", 0)
    max_size_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else 0
    backup_count = _parse_int_env("LOG_FILE_BACKUP_COUNT", 5, minimum=1)

    return LogSettings(
        log_root=log_root.resolve(),
        retention_days=retention_days,
        file_name_template=file_name_template,
        files_per_day=files_per_day,
        max_size_bytes=max_size_bytes,
        backup_count=backup_count,
    )


class HourlyDateFolderHandler(logging.Handler):
    """
    应用主日志 Handler：
    - 根目录下按日期命名文件夹（YYYY-MM-DD）
    - 每个文件夹内按 env 配置的个数与时间片切分日志文件
    - 可选单文件大小上限与备份文件个数
    - 超过保留天数的日期文件夹自动删除
    """

    def __init__(self, settings: LogSettings, encoding: str = "utf-8"):
        super().__init__()
        self.settings = settings
        self.log_root = settings.log_root
        self.retention_days = settings.retention_days
        self.file_name_template = settings.file_name_template
        self.files_per_day = settings.files_per_day
        self.max_size_bytes = settings.max_size_bytes
        self.backup_count = settings.backup_count
        self.encoding = encoding
        self._stream = None
        self._current_path: Path | None = None
        self._current_slot: tuple[str, int] | None = None

    def _slot_index(self, now: datetime) -> int:
        return min(self.files_per_day - 1, int(now.hour * self.files_per_day / 24))

    def _render_file_name(self, date_str: str, slot: int, hour: int) -> str:
        return self.file_name_template.format(date=date_str, slot=slot, hour=hour)

    def _log_path(self, date_str: str, slot: int, hour: int) -> Path:
        file_name = self._render_file_name(date_str, slot, hour)
        return self.log_root / date_str / file_name

    def _rotate_by_size(self, path: Path) -> None:
        for index in range(self.backup_count - 1, 0, -1):
            src = path.with_name(f"{path.name}.{index}")
            dst = path.with_name(f"{path.name}.{index + 1}")
            if dst.exists():
                dst.unlink()
            if src.exists():
                src.rename(dst)
        if path.exists():
            path.rename(path.with_name(f"{path.name}.1"))

    def _open_stream(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if self._stream:
            self._stream.close()
        self._stream = open(path, "a", encoding=self.encoding)
        self._current_path = path

    def _maybe_rotate(self, now: datetime) -> None:
        date_str = now.strftime("%Y-%m-%d")
        slot = self._slot_index(now)
        slot_key = (date_str, slot)
        path = self._log_path(date_str, slot, now.hour)

        if slot_key != self._current_slot:
            self._open_stream(path)
            self._current_slot = slot_key
            self._cleanup_expired(now)
            return

        if (
            self.max_size_bytes > 0
            and self._current_path == path
            and path.exists()
            and path.stat().st_size >= self.max_size_bytes
        ):
            if self._stream:
                self._stream.close()
                self._stream = None
            self._rotate_by_size(path)
            self._open_stream(path)

    def _cleanup_expired(self, now: datetime) -> None:
        if self.retention_days <= 0 or not self.log_root.is_dir():
            return
        cutoff = (now - timedelta(days=self.retention_days)).date()
        for entry in self.log_root.iterdir():
            if not entry.is_dir():
                continue
            try:
                folder_date = datetime.strptime(entry.name, "%Y-%m-%d").date()
            except ValueError:
                continue
            if folder_date < cutoff:
                shutil.rmtree(entry, ignore_errors=True)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with self.lock:
                now = datetime.fromtimestamp(record.created)
                self._maybe_rotate(now)
                msg = self.format(record)
                self._stream.write(msg + "\n")
                self._stream.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        with self.lock:
            if self._stream:
                self._stream.close()
                self._stream = None
            self._current_path = None
        super().close()


def _get_shared_file_handler(level: int) -> HourlyDateFolderHandler:
    global _shared_file_handler
    if _shared_file_handler is None:
        settings = get_log_settings()
        _shared_file_handler = HourlyDateFolderHandler(settings)
        _shared_file_handler.setLevel(level)
        _shared_file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    return _shared_file_handler


def setup_logger(name: str, log_file: str | None = None, level: int = logging.INFO):
    """
    配置日志记录器。

    log_file 参数已废弃，保留仅为兼容旧调用；实际写入行为由 env 中
    LOG_PATH / LOG_FILE_NAME / LOG_FILES_PER_DAY / LOG_FILE_MAX_SIZE_MB /
    LOG_FILE_BACKUP_COUNT / LOG_RETENTION_DAYS 控制。
    """
    _ = log_file

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    file_handler = _get_shared_file_handler(level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
