from loguru import logger
import sys


def setup_logger():
    """Настройка логгера"""
    logger.remove()

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
        "<level>{message}</level>",
        level="INFO",
        colorize=True,
    )

    logger.add(
        "logs/taxi_agent_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
        level="DEBUG",
        serialize=True,
    )

    return logger
