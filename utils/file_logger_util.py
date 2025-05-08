import logging
import os

# Import logging configuration
from .logging_config import get_log_directory, get_logging_level # Import necessary config

def setup_file_handler(logger: logging.Logger, service_name: str):
    """Sets up and adds a file handler to the given logger, using config from logging_config."""
    log_dir = get_log_directory()
    logging_level = get_logging_level()

    log_file_path = os.path.join(log_dir, f"{service_name}_debug.log")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging_level) # Log according to environment variable

    # Create a formatter and add it to the handler (formatter still needs service_name)
    formatter = logging.Formatter(f"%(asctime)s [%(levelname)s] [{service_name}] %(message)s")
    file_handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(file_handler) 