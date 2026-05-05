import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from app.core.config import settings


def setup_logger(name: str) -> logging.Logger:
    """创建并配置logger"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = TimedRotatingFileHandler(
        filename=str(log_dir / "empi"),
        when='midnight',
        interval=1,
        backupCount=settings.LOG_RETENTION_DAYS,
        encoding='utf-8'
    )

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    logger = logging.getLogger(name)
    return logger if logger.handlers else setup_logger(name)