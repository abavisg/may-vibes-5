import logging
import os
import sys # Import sys for StreamHandler
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Map environment variable string to logging level
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "DEBUG").upper()
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Determine the logging level, default to DEBUG if not recognized
logging_level = LOG_LEVEL_MAP.get(LOGGING_LEVEL, logging.DEBUG)

# Custom filter to allow only INFO level messages for console
class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.INFO

# Get logger instance
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set logger level to DEBUG to capture all messages before filtering

# Create console handler and set level to DEBUG, add InfoFilter to show only INFO in console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG) # Process all messages from logger
console_handler.addFilter(InfoFilter()) # Only pass INFO level to console

# Create file handler and set level to the determined logging level
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "signal_generator_debug.log"))
file_handler.setLevel(logging_level) # Log according to environment variable

# Create a formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s [%(levelname)s] [signal_generator] %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Log the effective logging level for the file handler
logger.info(f"Signal generator service file logging level set to {logging.getLevelName(file_handler.level)}")

# Load environment variables
load_dotenv()

# Import the ServiceLogger
from utils.logging_utils import ServiceLogger

# Initialize the logger for the signal generator service
logger = ServiceLogger("signal_generator").get_logger()

app = FastAPI(
    title="Signal Generator",
    description="Service to generate trading signals from detected patterns",
    version="0.1.0"
)

class PatternDetection(BaseModel):
    patterns: list
    candle: dict

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    return response

@app.post("/generate")
async def generate_signal(pattern_detection: PatternDetection):
    logger.info(f"[START] /generate for {pattern_detection.candle.get('symbol', 'unknown')} at {pattern_detection.candle.get('timestamp', 'unknown')}")
    logger.info(f"Input: {pattern_detection.dict()}")
    try:
        patterns = pattern_detection.patterns
        candle = pattern_detection.candle
        if not patterns:
            result = {"status": "no_signal"}
            logger.info(f"Output: {result}")
            logger.info(f"[END] /generate for {candle.get('symbol', 'unknown')} at {candle.get('timestamp', 'unknown')}")
            return result
        # Example: generate a dummy signal
        pattern = patterns[0]
        signal = {
            "id": os.urandom(8).hex(),
            "timestamp": candle.get("timestamp"),
            "symbol": candle.get("symbol"),
            "candle_timestamp": candle.get("timestamp"),
            "type": "BUY" if pattern.get("type") == "bullish" else "SELL",
            "entry_price": candle.get("close"),
            "stop_loss": candle.get("close", 0) * 1.01,
            "take_profit": candle.get("close", 0) * 0.98,
            "type_of_data": candle.get("type_of_data", "DUMMY"),
            "pattern": pattern
        }
        logger.info(f"Output: {signal}")
        logger.info(f"[END] /generate for {candle.get('symbol', 'unknown')} at {candle.get('timestamp', 'unknown')}")
        return signal
    except Exception as e:
        logger.error(f"Error generating signal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating signal: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "signal_generator"}

@app.on_event("startup")
async def startup_event():
    logger.info("Signal generator service started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Signal generator service stopped.") 