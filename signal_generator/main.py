import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
    # Extract pattern and price information
    pattern_type = pattern_data["pattern"]
    pattern_strength = pattern_data["strength"]
    current_price = candle_data["close"]
    
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
        
    elif pattern_type == "bearish" and pattern_strength > 30:
        signal_type = "SELL"
        entry_price = current_price
        
        # Set stop loss 0.5% above entry
        stop_loss = round(entry_price * 1.005, 2)
        
        # Set take profit 1.5% below entry (3:1 risk-reward ratio)
        take_profit = round(entry_price * 0.985, 2)
    
    # Generate signal ID
    signal_id = str(uuid.uuid4())
    
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
    
    logger.info(f"Generated signal: {signal}")
    
    return signal

# Define API endpoints
@app.post("/generate")
async def generate_trading_signal(request: GenerateSignalRequest):
    """
    Generate a trading signal based on a detected pattern and candle data
    """
    logger.info(f"Generating signal from pattern: {request.pattern} and candle: {request.candle}")
    
    try:
        # Convert Pydantic models to dict
        pattern_dict = request.pattern.dict()
        candle_dict = request.candle.dict()
        
        # Generate signal
        signal = generate_signal(pattern_dict, candle_dict)
        
        return signal
    except Exception as e:
        logger.error(f"Error generating signal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating signal: {str(e)}")

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "signal_generator"} 