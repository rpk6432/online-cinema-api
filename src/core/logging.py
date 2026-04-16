import sys

from loguru import logger


def setup_logging(log_level: str = "DEBUG", json_format: bool = False) -> None:
    """Configure loguru for the application."""
    logger.remove()

    if json_format:
        logger.add(sys.stdout, level=log_level, serialize=True)
    else:
        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level:<8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
                "<level>{message}</level>"
            ),
        )
