import logging
import os

# Map environment variable string to logging level
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Determine the logging level from environment variable, default to DEBUG if not recognized
LOGGING_LEVEL_STR = os.getenv("LOGGING_LEVEL", "DEBUG").upper()
LOGGING_LEVEL = LOG_LEVEL_MAP.get(LOGGING_LEVEL_STR, logging.DEBUG)

# Ensure logs directory exists (needed by file logger, but config is a good place for this constant)
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Provide easy access to the determined level and log directory
def get_logging_level() -> int:
    return LOGGING_LEVEL

def get_log_directory() -> str:
    return LOG_DIR

def get_level_map() -> dict:
    return LOG_LEVEL_MAP 