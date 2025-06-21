from loguru import logger
from rich.console import Console

console = Console()

# Configure loguru to use rich for formatting
logger.remove()

LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>"
logger.add(lambda msg: console.print(msg, end=""), colorize=True, format=LOG_FORMAT)

__all__ = ["logger", "console"]
