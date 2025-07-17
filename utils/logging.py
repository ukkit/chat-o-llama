"""Logging configuration for Chat-O-Llama."""

import logging


def setup_logging(level=logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(level=level)
    logger = logging.getLogger(__name__)
    return logger