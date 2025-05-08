import logging
import sys

# Import logging configuration
from .logging_config import get_logging_level, get_level_map, get_level_name_map

# Import the console and file handler setup utilities
from .console_logger import setup_console_handler
from .file_logger_util import setup_file_handler

class ServiceLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._logger = logging.getLogger(service_name)
        self._logger.setLevel(logging.DEBUG) # Set logger level to DEBUG to capture all messages before filtering

        # Determine the logging level, default to DEBUG if not recognized
        # This logic is now in logging_config, just need to get the level
        self.logging_level = get_logging_level()

        # Prevent adding handlers multiple times if the logger is retrieved elsewhere
        if not self._logger.handlers:
            # Setup console handler using the utility function
            setup_console_handler(self._logger, self.service_name)

            # Setup file handler using the utility function
            setup_file_handler(self._logger, self.service_name)

        # Log the effective logging level for the handlers
        # Need the level name, can get from logging_config
        level_name = get_level_name_map().get(self.logging_level, 'UNKNOWN')
        self._logger.info(f"Service '{service_name}' console and file logging level set to {level_name}")

    def get_logger(self) -> logging.Logger:
        return self._logger 