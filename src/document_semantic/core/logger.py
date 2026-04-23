"""Loguru logger configuration for the document semantic pipeline."""

import os
import sys

from loguru import logger

# Log level from environment variable, default to INFO
_LOG_LEVEL = os.getenv("DOC_SEMANTIC_LOG_LEVEL", "INFO").upper()

# Remove default handler
logger.remove()

# Add stdout handler with configurable level and structured format
logger.add(
    sys.stderr,
    level=_LOG_LEVEL,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    enqueue=True,  # Thread-safe
)


def get_logger(name: str = __name__):
    """Get a logger instance bound to the given name.

    Args:
        name: Logger name, typically the module's __name__.

    Returns:
        A loguru logger instance.
    """
    return logger.bind(name=name)


__all__ = ["get_logger"]
