import logging
import os
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [pattern_detector] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Pattern detector service starting up")

# Feature flags
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() == "true"
logger.info(f"USE_SIGNAL_STUBS set to: {USE_SIGNAL_STUBS}")

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

# Pattern detection functions
def detect_pattern(candle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple pattern detection logic for demonstration.
    
    For a real implementation, you would use more sophisticated technical analysis,
    possibly incorporating multiple candles and various indicators.
    """
    logger.info(f"Analyzing candle data for {candle['symbol']} at {candle['timestamp']}")
    
    # Extract required data
    open_price = candle["open"]
    close_price = candle["close"]
    high_price = candle["high"]
    low_price = candle["low"]
    
    # Calculate candle body size (absolute value)
    body_size = abs(close_price - open_price)
    
    # Calculate upper and lower shadows
    if close_price >= open_price:  # Bullish candle
        upper_shadow = high_price - close_price
        lower_shadow = open_price - low_price
        logger.debug(f"Bullish candle detected: body={body_size}, upper_shadow={upper_shadow}, lower_shadow={lower_shadow}")
    else:  # Bearish candle
        upper_shadow = high_price - open_price
        lower_shadow = close_price - low_price
        logger.debug(f"Bearish candle detected: body={body_size}, upper_shadow={upper_shadow}, lower_shadow={lower_shadow}")
    
    # Price difference threshold (simple version - in a real system this would be more sophisticated)
    threshold = 0.001 * open_price  # 0.1% of open price
    logger.debug(f"Using price threshold of {threshold}")
    
    # Simple pattern detection logic
    pattern_name = "neutral"
    pattern_strength = 0
    
    # Bullish pattern: Close significantly higher than open
    if close_price > open_price and (close_price - open_price) > threshold:
        pattern_name = "bullish"
        pattern_strength = min(100, int((close_price - open_price) / threshold * 10))
        logger.info(f"Bullish pattern detected with strength {pattern_strength}")
    
    # Bearish pattern: Close significantly lower than open
    elif open_price > close_price and (open_price - close_price) > threshold:
        pattern_name = "bearish"
        pattern_strength = min(100, int((open_price - close_price) / threshold * 10))
        logger.info(f"Bearish pattern detected with strength {pattern_strength}")
    else:
        logger.info(f"Neutral pattern detected")
    
    # Return the detected pattern
    pattern_result = {
        "pattern": pattern_name,
        "strength": pattern_strength,
        "details": {
            "body_size": body_size,
            "upper_shadow": upper_shadow,
            "lower_shadow": lower_shadow
        },
        "candle_timestamp": candle["timestamp"]
    }
    
    logger.info(f"Pattern detection completed: {pattern_name} with strength {pattern_strength}")
    return pattern_result

# Middleware to log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Received {request.method} request at {request.url.path}")
    response = await call_next(request)
    logger.info(f"Returning response with status code: {response.status_code}")
    return response

# Define API endpoints
@app.post("/detect")
async def detect_candle_pattern(candle: Candle) -> PatternResponse:
    """
    Analyze a candle for patterns and return the detection results
    """
    logger.info(f"Received candle data for pattern detection: {candle.symbol} at {candle.timestamp}")
    logger.debug(f"Full candle data: {candle.json()}")
    
    try:
        # Convert Pydantic model to dict
        candle_dict = candle.dict()
        
        # Check if we're using signal stubs
        if USE_SIGNAL_STUBS:
            logger.info("Using signal stubs, returning empty pattern list")
            # When using signal stubs, we don't need to detect patterns
            # Just return an empty pattern list
            return PatternResponse(
                patterns=[],
                candle=candle
            )
        
        # Detect pattern (only if not using stubs)
        logger.info("Starting pattern detection process")
        pattern_result = detect_pattern(candle_dict)
        
        # Return in the format expected by the signal generator
        logger.info(f"Returning detection results: {pattern_result['pattern']} with strength {pattern_result['strength']}")
        return PatternResponse(
            patterns=[pattern_result],
            candle=candle
        )
    except Exception as e:
        error_msg = f"Error analyzing candle: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check endpoint called")
    return {"status": "healthy", "service": "pattern_detector"}

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Pattern detector service is ready to receive requests") 