import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

_shared_file_handler: "HourlyDateFolderHandler | None" = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _load_env() -> None:
    env_path = _project_root() / "global_config" / "env"
    load_dotenv(dotenv_path=env_path, override=True)


def get_log_settings() -> tuple[Path, int]:
    """从 env 读取日志保留路径与保留天数。"""
    _load_env()
    root = _project_root()
    relative = os.getenv("LOG_RETENTION_PATH", "logs").strip()
    log_root = Path(relative) if Path(relative).is_absolute() else root / relative
    retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    return log_root.resolve(), retention_days


class HourlyDateFolderHandler(logging.Handler):
    """
    应用主日志 Handler：
    - 根目录下按日期命名文件夹（YYYY-MM-DD）
    - 每个文件夹 24 个文件（00.log ~ 23.log），每小时一个
    - 超过保留天数的日期文件夹自动删除
    """

    def __init__(self, log_root: Path, retention_days: int, encoding: str = "utf-8"):
        super().__init__()
        self.log_root = Path(log_root)
        self.retention_days = retention_days
        self.encoding = encoding
        self._stream = None
        self._current_slot: tuple[str, int] | None = None

    def _log_path(self, date_str: str, hour: int) -> Path:
        return self.log_root / date_str / f"{hour:02d}.log"

    def _open_stream(self, date_str: str, hour: int) -> None:
        path = self._log_path(date_str, hour)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self._stream:
            self._stream.close()
        self._stream = open(path, "a", encoding=self.encoding)

    def _maybe_rotate(self, now: datetime) -> None:
        slot = (now.strftime("%Y-%m-%d"), now.hour)
        if slot != self._current_slot:
            self._open_stream(*slot)
            self._current_slot = slot
            self._cleanup_expired(now)

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
        super().close()


def _get_shared_file_handler(level: int) -> HourlyDateFolderHandler:
    global _shared_file_handler
    if _shared_file_handler is None:
        log_root, retention_days = get_log_settings()
        _shared_file_handler = HourlyDateFolderHandler(log_root, retention_days)
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

    log_file 参数已废弃，保留仅为兼容旧调用；实际写入路径由 env 中
    LOG_RETENTION_PATH / LOG_RETENTION_DAYS 控制。
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
