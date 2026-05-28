from .logger_config import setup_logger

logger = setup_logger('backen-fastapi', 'app.log')
write_fid_logger = setup_logger('write_fid', 'app.log')
