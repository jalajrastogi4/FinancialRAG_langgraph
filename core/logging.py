import os
from pathlib import Path
from loguru import logger

logger.remove()

logger = logger.bind(thread_id="-", user_id="-")

LOG_DIR = os.path.join(Path(__file__).resolve().parent.parent, 'logs')

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "thread={extra[thread_id]} user={extra[user_id]} | "
    "{message} | extras={extra}"
)

logger.add(
    sink=os.path.join(LOG_DIR, "debug.log"),
    format=LOG_FORMAT,
    level="DEBUG",
    filter=lambda record: record["level"].no <= logger.level("WARNING").no,
    rotation="10MB",
    retention="30 days",
    compression="zip",
)

logger.add(
    sink=os.path.join(LOG_DIR, "error.log"),
    format=LOG_FORMAT,
    level="ERROR",
    rotation="10MB",
    retention="30 days",
    compression="zip",
    backtrace=True,
    diagnose=True,
)


def get_logger():
    return logger