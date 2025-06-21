from loguru import logger
from rich.console import Console

console = Console()

# Configure loguru to use rich for simple colored messages only
logger.remove()

LOG_FORMAT = "<level>{message}</level>"
logger.add(lambda msg: console.print(msg, end=""), colorize=True, format=LOG_FORMAT)

__all__ = ["logger", "console"]
