import logging
import os
import sys

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Map environment variable string to logging level
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Custom filter to allow only INFO level messages for console
# class InfoFilter(logging.Filter):
#     def filter(self, record):
#         return record.levelno == logging.INFO

class ServiceLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._logger = logging.getLogger(service_name)
        self._logger.setLevel(logging.DEBUG) # Set logger level to DEBUG to capture all messages before filtering

        # Determine the logging level, default to DEBUG if not recognized
        logging_level_str = os.getenv("LOGGING_LEVEL", "DEBUG").upper()
        self.logging_level = LOG_LEVEL_MAP.get(logging_level_str, logging.DEBUG)

        # Prevent adding handlers multiple times if the logger is retrieved elsewhere
        if not self._logger.handlers:
            # Create console handler and set level to the determined logging level
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.logging_level) # Set console output level based on env var
            # console_handler.addFilter(InfoFilter()) # Only pass INFO level to console

            # Create file handler and set level to the determined logging level
            log_file_path = os.path.join(LOG_DIR, f"{service_name}_debug.log")
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(self.logging_level) # Log according to environment variable

            # Create a formatter and add it to the handlers
            formatter = logging.Formatter(f"%(asctime)s [%(levelname)s] [{service_name}] %(message)s")
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            # Add the handlers to the logger
            self._logger.addHandler(console_handler)
            self._logger.addHandler(file_handler)

        # Log the effective logging level for the file handler
        self._logger.info(f"Service '{service_name}' console and file logging level set to {logging.getLevelName(self.logging_level)}")

    def get_logger(self) -> logging.Logger:
        return self._logger 