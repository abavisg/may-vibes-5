import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [signal_generator] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Signal generator service starting up")

# Feature flags
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() == "true"
logger.info(f"USE_SIGNAL_STUBS set to: {USE_SIGNAL_STUBS}")

# Import stubs if feature flag is enabled
if USE_SIGNAL_STUBS:
    from signal_generator.signal_stubs import BuySignalStub, SellSignalStub
    logger.info("Using signal stubs for signal generation")
    # Initialize stubs with configurable frequencies
    buy_frequency = float(os.getenv("BUY_SIGNAL_FREQUENCY", "0.3"))
    sell_frequency = float(os.getenv("SELL_SIGNAL_FREQUENCY", "0.3"))
    logger.info(f"Configured stub frequencies - BUY: {buy_frequency}, SELL: {sell_frequency}")
    buy_stub = BuySignalStub(frequency=buy_frequency)
    sell_stub = SellSignalStub(frequency=sell_frequency)

# Create FastAPI application
app = FastAPI(
    title="Signal Generator",
    description="Service to generate trading signals based on detected patterns",
    version="0.1.0"
)

# Define request models
class CandleData(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class PatternData(BaseModel):
    pattern: str
    strength: int
    details: Dict[str, float]
    candle_timestamp: str

class PatternDetection(BaseModel):
    patterns: List[Dict[str, Any]]
    candle: CandleData

class GenerateSignalRequest(BaseModel):
    pattern: PatternData
    candle: CandleData

# Signal generation functions
def generate_signal(pattern_data: Dict[str, Any], candle_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a trading signal based on the detected pattern and candle data.
    
    In a real implementation, this would incorporate risk management,
    position sizing, and more sophisticated entry/exit strategies.
    """
    logger.info(f"Generating signal for {candle_data['symbol']} based on {pattern_data['pattern']} pattern")
    
    # Extract pattern and price information
    pattern_type = pattern_data["pattern"]
    pattern_strength = pattern_data["strength"]
    current_price = candle_data["close"]
    
    logger.debug(f"Pattern type: {pattern_type}, strength: {pattern_strength}, current price: {current_price}")
    
    # Default signal type (none)
    signal_type = "none"
    entry_price = None
    stop_loss = None
    take_profit = None
    
    # Signal generation logic
    if pattern_type == "bullish" and pattern_strength > 30:
        signal_type = "BUY"
        entry_price = current_price
        
        # Set stop loss 0.5% below entry
        stop_loss = round(entry_price * 0.995, 2)
        
        # Set take profit 1.5% above entry (3:1 risk-reward ratio)
        take_profit = round(entry_price * 1.015, 2)
        
        logger.info(f"Generated BUY signal at {entry_price} (stop: {stop_loss}, target: {take_profit})")
        
    elif pattern_type == "bearish" and pattern_strength > 30:
        signal_type = "SELL"
        entry_price = current_price
        
        # Set stop loss 0.5% above entry
        stop_loss = round(entry_price * 1.005, 2)
        
        # Set take profit 1.5% below entry (3:1 risk-reward ratio)
        take_profit = round(entry_price * 0.985, 2)
        
        logger.info(f"Generated SELL signal at {entry_price} (stop: {stop_loss}, target: {take_profit})")
    else:
        logger.info(f"No signal generated, pattern strength {pattern_strength} insufficient or neutral pattern")
    
    # Generate signal ID
    signal_id = str(uuid.uuid4())
    logger.debug(f"Generated signal ID: {signal_id}")
    
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create the signal
    signal = {
        "id": signal_id,
        "timestamp": timestamp,
        "symbol": candle_data["symbol"],
        "candle_timestamp": candle_data["timestamp"],
        "type": signal_type,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "pattern": {
            "type": pattern_type,
            "strength": pattern_strength
        }
    }
    
    logger.info(f"Signal details: ID={signal_id}, type={signal_type}, symbol={candle_data['symbol']}")
    
    return signal

# Middleware to log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Received {request.method} request at {request.url.path}")
    response = await call_next(request)
    logger.info(f"Returning response with status code: {response.status_code}")
    return response

# Define API endpoints
@app.post("/generate")
async def generate_signal_endpoint(pattern: PatternDetection) -> Dict[str, Any]:
    try:
        logger.info(f"Received pattern detection for {pattern.candle.symbol} at {pattern.candle.timestamp}")
        logger.debug(f"Full pattern data: {pattern.dict()}")
        
        # Extract candle data
        candle = pattern.candle.dict()
        
        # Check if we're using signal stubs
        if USE_SIGNAL_STUBS:
            logger.info(f"Using signal stubs for {candle['symbol']}")
            # Try to generate signals using stubs
            signals = []
            
            # Try to generate BUY signal
            logger.debug(f"Checking for BUY stub signal")
            buy_signal = buy_stub.analyze(candle)
            if buy_signal:
                logger.info(f"BUY stub signal generated for {candle['symbol']}")
                signals.append(buy_signal)
                
            # Try to generate SELL signal
            logger.debug(f"Checking for SELL stub signal")
            sell_signal = sell_stub.analyze(candle)
            if sell_signal:
                logger.info(f"SELL stub signal generated for {candle['symbol']}")
                signals.append(sell_signal)
                
            if signals:
                # Return the first signal (could be either BUY or SELL)
                logger.info(f"Returning stub signal: {signals[0]['type']} for {signals[0]['symbol']}")
                return signals[0]
            else:
                # No signal generated
                logger.info(f"No stub signals generated for {candle['symbol']}")
                return {"status": "no_signal", "message": "No trading signals generated for this pattern"}
        
        # If not using stubs, use the actual signal generation logic
        logger.info(f"Using real signal generation logic for {candle['symbol']}")
        patterns = pattern.patterns
        
        # Check if we have patterns to analyze
        if not patterns:
            logger.info(f"No patterns detected for {candle['symbol']}, cannot generate signals")
            return {
                "status": "no_signal",
                "message": "No patterns detected to generate signals from"
            }
        
        logger.info(f"Analyzing {len(patterns)} patterns for signal generation")
        
        # For now, just use the first pattern (in a real system we might prioritize or combine them)
        first_pattern = patterns[0]
        
        # Generate a signal based on the pattern
        signal = generate_signal(first_pattern, candle)
        
        # Check if we generated an actionable signal
        if signal["type"] != "none":
            logger.info(f"Generated actionable {signal['type']} signal for {signal['symbol']}")
            return signal
        else:
            logger.info(f"No actionable signal generated for {candle['symbol']}")
            return {
                "status": "no_signal",
                "message": "No trading signals generated for this pattern"
            }
            
    except Exception as e:
        error_msg = f"Error generating signal: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check endpoint called")
    return {"status": "healthy", "service": "signal_generator"}

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Signal generator service is ready to receive requests") 