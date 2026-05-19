"""日志工具"""
import sys
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = None):
    """
    配置日志

    Args:
        log_level: 日志级别
        log_file: 日志文件路径
    """
    # 移除默认handler
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # 添加文件输出（如果指定）
    if log_file:
        logger.add(
            log_file,
            rotation="10 MB",
            retention="7 days",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
        )

    return logger


# 默认logger实例
default_logger = setup_logger()
