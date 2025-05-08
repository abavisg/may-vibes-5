import logging
import sys

# Import logging configuration
from .logging_config import get_logging_level

def setup_console_handler(logger: logging.Logger, service_name: str):
    """Sets up and adds a console handler to the given logger, using config from logging_config."""
    console_handler = logging.StreamHandler(sys.stdout)
    # Set console output level based on the centralized logging level
    console_handler.setLevel(get_logging_level())

    # Create a formatter and add it to the handler (formatter still needs service_name)
    formatter = logging.Formatter(f"%(asctime)s [%(levelname)s] [{service_name}] %(message)s")
    console_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(console_handler) 