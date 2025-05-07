import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
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

# Configuration
SIGNAL_LOG_DIR = os.getenv("SIGNAL_LOG_DIR", "./signal_logs")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", None)

# Create log directory if it doesn't exist
os.makedirs(SIGNAL_LOG_DIR, exist_ok=True)

# Create FastAPI application
app = FastAPI(
    title="Signal Dispatcher",
    description="Service to dispatch trading signals to various outputs",
    version="0.1.0"
)

# Define request model
class TradingSignal(BaseModel):
    id: str
    timestamp: str
    symbol: str
    candle_timestamp: str
    type: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pattern: Dict[str, Any]

# Signal dispatching functions
def log_signal_to_file(signal: Dict[str, Any]) -> str:
    """Log the signal to a file"""
    # Create a filename based on date
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(SIGNAL_LOG_DIR, f"signals_{today}.json")
    
    # Format the signal as pretty JSON
    signal_json = json.dumps(signal, indent=2)
    
    # Append to the log file
    with open(log_file, "a") as f:
        f.write(signal_json + "\n\n")
    
    logger.info(f"Signal logged to file: {log_file}")
    
    return log_file

async def send_signal_to_webhook(signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send the signal to a webhook if configured"""
    if not WEBHOOK_URL:
        logger.info("No webhook URL configured, skipping webhook dispatch")
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(WEBHOOK_URL, json=signal)
            response.raise_for_status()
            logger.info(f"Signal sent to webhook: {WEBHOOK_URL}")
            return response.json()
    except Exception as e:
        logger.error(f"Error sending signal to webhook: {str(e)}")
        return {"error": str(e)}

def format_signal_for_human(signal: Dict[str, Any]) -> str:
    """Format the signal for human-readable output"""
    signal_type = signal["type"]
    
    if signal_type == "none" or signal.get("status") == "no_signal":
        return "NO SIGNAL GENERATED"
    
    symbol = signal["symbol"]
    entry_price = signal["entry_price"]
    stop_loss = signal["stop_loss"]
    take_profit = signal["take_profit"]
    
    # Extract pattern information (handle both real patterns and stubs)
    pattern = signal["pattern"]
    pattern_type = pattern["type"]
    
    # Check if it's a stub pattern (has confidence instead of strength)
    if "confidence" in pattern:
        pattern_strength = int(pattern["confidence"] * 100)
        pattern_description = pattern.get("description", "")
    else:
        pattern_strength = pattern.get("strength", 0)
        pattern_description = ""
    
    # Calculate potential profit/loss
    if signal_type == "BUY":
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:  # SELL
        risk = stop_loss - entry_price
        reward = entry_price - take_profit
    
    risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
    
    # Format the message
    message = f"""
🔔 SIGNAL ALERT 🔔
Symbol: {symbol}
Action: {signal_type}
Pattern: {pattern_type.upper()} (Strength: {pattern_strength}%)
{pattern_description}
Entry: {entry_price}
Stop Loss: {stop_loss}
Take Profit: {take_profit}
Risk/Reward: 1:{risk_reward_ratio}
Timestamp: {signal["timestamp"]}
ID: {signal["id"]}
"""
    
    return message

# Define API endpoints
@app.post("/dispatch")
async def dispatch_signal(signal: TradingSignal):
    """
    Dispatch a trading signal to various outputs (file log, webhook, etc.)
    """
    logger.info(f"Dispatching signal: {signal.json()}")
    
    try:
        # Convert Pydantic model to dict
        signal_dict = signal.dict()
        
        # Format signal for human-readable output
        human_readable = format_signal_for_human(signal_dict)
        logger.info(f"Signal formatted for human:\n{human_readable}")
        
        # Log to file
        log_file = log_signal_to_file(signal_dict)
        
        # Send to webhook if configured
        webhook_result = await send_signal_to_webhook(signal_dict)
        
        return {
            "status": "success",
            "message": "Signal dispatched successfully",
            "outputs": {
                "log_file": log_file,
                "webhook_result": webhook_result,
                "human_readable": human_readable
            }
        }
    except Exception as e:
        logger.error(f"Error dispatching signal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error dispatching signal: {str(e)}")

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "signal_dispatcher"} 