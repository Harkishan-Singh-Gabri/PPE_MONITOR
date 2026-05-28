from loguru import logger
import sys

def setup_logger():
    logger.remove() #remove default handler

    #terminal
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{module}</cyan> — {message}",
        level="DEBUG"
    )

    #file - full logs saved
    logger.add(
        "logs/ppe_monitor.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    return logger

log=setup_logger()