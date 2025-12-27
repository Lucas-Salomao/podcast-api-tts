"""
Logging configuration for the Podcast Generator API.
"""

import logging
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """
    Configures and returns the application logger.
    """
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


# Logger instance for import
logger = setup_logging()
