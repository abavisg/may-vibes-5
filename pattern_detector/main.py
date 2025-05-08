import logging
import os
import sys # Import sys for StreamHandler
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import time # Import time for measuring duration

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
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "pattern_detector_debug.log"))
file_handler.setLevel(logging_level) # Log according to environment variable

# Create a formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s [%(levelname)s] [pattern_detector] %(message)s")
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Log the effective logging level for the file handler
logger.info(f"Pattern detector service file logging level set to {logging.getLevelName(file_handler.level)}")

# Import our Ollama client
from pattern_detector.ollama_client import detect_patterns_with_ollama, detect_pattern_fallback

# Load environment variables
load_dotenv()

# Import the ServiceLogger
from utils.logging_utils import ServiceLogger

# Initialize the logger for the pattern detector service
logger = ServiceLogger("pattern_detector").get_logger()

# Feature flags
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

# Create FastAPI application
app = FastAPI(
    title="Pattern Detector",
    description="Service to detect patterns in candle data",
    version="0.1.0"
)

# Define request model
class Candle(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class PatternResponse(BaseModel):
    patterns: List[Dict[str, Any]]
    candle: Candle

# Middleware to log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    return response

# Define API endpoints
@app.post("/detect")
async def detect_candle_pattern(candle: Candle) -> PatternResponse:
    logger.info(f"[START] /detect for {candle.symbol} at {candle.timestamp}")
    logger.info(f"Input: {candle.dict()}")
    try:
        candle_dict = candle.dict()
        patterns = []
        if USE_OLLAMA:
            logger.info(f"Using Ollama for pattern detection for {candle.symbol}")
            try:
                patterns = await detect_patterns_with_ollama(candle_dict)
                if not patterns:
                    logger.info(f"Ollama detected no patterns for {candle.symbol}")
            except Exception as e:
                logger.error(f"Ollama pattern detection failed for {candle.symbol}: {e}. Falling back.")
                fallback_pattern = detect_pattern_fallback(candle_dict)
                patterns = [fallback_pattern] if fallback_pattern["strength"] > 0 else []
                if patterns:
                    logger.info(f"Fallback detected a pattern for {candle.symbol}")
                else:
                    logger.info(f"Fallback detected no patterns for {candle.symbol}")
        else:
            logger.info(f"Ollama is disabled. Using fallback pattern detection for {candle.symbol}")
            fallback_pattern = detect_pattern_fallback(candle_dict)
            patterns = [fallback_pattern] if fallback_pattern["strength"] > 0 else []
            if patterns:
                logger.info(f"Fallback detected a pattern for {candle.symbol}")
            else:
                logger.info(f"Fallback detected no patterns for {candle.symbol}")

        result = PatternResponse(patterns=patterns, candle=candle)
        logger.info(f"Output: {result.dict()}")
        logger.info(f"[END] /detect for {candle.symbol} at {candle.timestamp}")
        return result
    except Exception as e:
        logger.error(f"Error analyzing candle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing candle: {str(e)}")

@app.get("/health")
async def health_check():
    logger.info("[HEALTH] pattern_detector healthy check")
    return {"status": "healthy", "service": "pattern_detector"}

@app.post("/explain")
async def explain_candle_pattern(candle: Candle):
    logger.info(f"[START] /explain for {candle.symbol} at {candle.timestamp}")
    logger.info(f"Input: {candle.dict()}")
    try:
        candle_dict = candle.dict()
        if not USE_OLLAMA:
            result = {
                "explanation": "Pattern explanation requires Ollama integration to be enabled (USE_OLLAMA=true)",
                "candle": candle
            }
            logger.info(f"Output: {result}")
            logger.info(f"[END] /explain for {candle.symbol} at {candle.timestamp}")
            return result
        patterns = await detect_patterns_with_ollama(candle_dict)
        if not patterns:
            result = {
                "explanation": "No significant patterns detected in this candle",
                "patterns": [],
                "candle": candle
            }
            logger.info(f"Output: {result}")
            logger.info(f"[END] /explain for {candle.symbol} at {candle.timestamp}")
            return result
        pattern_names = ", ".join([p.get("pattern", "unknown") for p in patterns])
        explanations = []
        for p in patterns:
            pattern_type = p.get("type", "neutral").upper()
            strength = p.get("strength", 0)
            description = p.get("description", "No description available")
            prediction = p.get("prediction", "No prediction available")
            explanation = f"{p.get('pattern', 'Unknown Pattern')} ({pattern_type}, Strength: {strength}/100): {description}. {prediction}"
            explanations.append(explanation)
        full_explanation = f"Detected pattern(s): {pattern_names}\n\n" + "\n\n".join(explanations)
        result = {
            "explanation": full_explanation,
            "patterns": patterns,
            "candle": candle
        }
        logger.info(f"Output: {result}")
        logger.info(f"[END] /explain for {candle.symbol} at {candle.timestamp}")
        return result
    except Exception as e:
        logger.error(f"Error explaining candle pattern: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error explaining candle pattern: {str(e)}")

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Pattern detector service started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Pattern detector service stopped.") 