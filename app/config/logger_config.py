import logging
import os


def setup_logger(name, log_file='app.log', level=logging.INFO):
    """配置日志记录器"""

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 获取项目根目录（logger_config.py所在目录）
    # root_dir = os.path.dirname(os.path.abspath(__file__))
    #  日志文件放在项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_path = os.path.join(root_dir, log_file)

    # 创建文件handler
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(level)

    # 创建控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加handler到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
