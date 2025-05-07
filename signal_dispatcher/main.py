import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [signal_dispatcher] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Signal dispatcher service starting up")

# Configuration
SIGNAL_LOG_DIR = os.getenv("SIGNAL_LOG_DIR", "./signal_logs")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", None)

logger.info(f"SIGNAL_LOG_DIR: {SIGNAL_LOG_DIR}")
logger.info(f"WEBHOOK_URL: {WEBHOOK_URL if WEBHOOK_URL else 'Not configured'}")

# Create log directory if it doesn't exist
os.makedirs(SIGNAL_LOG_DIR, exist_ok=True)
logger.info(f"Ensured signal log directory exists: {SIGNAL_LOG_DIR}")

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
    """Log the signal to a file as part of a valid JSON array"""
    # Create a filename based on date
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(SIGNAL_LOG_DIR, f"signals_{today}.json")
    
    logger.info(f"Logging signal ID {signal['id']} to file: {log_file}")
    
    # Check if file exists
    if os.path.exists(log_file):
        try:
            # Read the existing file
            with open(log_file, 'r') as f:
                content = f.read().strip()
                
            if not content:
                # File exists but is empty
                signals = []
            else:
                try:
                    # Try to parse existing content as JSON
                    signals = json.loads(content)
                    if not isinstance(signals, list):
                        # Convert to list if not already
                        logger.warning(f"Converting existing non-array content to array format")
                        signals = [signals]
                except json.JSONDecodeError:
                    # If the existing file isn't valid JSON, start fresh
                    logger.warning(f"Existing signals file wasn't valid JSON, starting fresh")
                    signals = []
        except Exception as e:
            logger.error(f"Error reading existing signals file: {str(e)}", exc_info=True)
            signals = []
    else:
        # File doesn't exist, start with empty array
        signals = []
    
    # Add the new signal
    signals.append(signal)
    
    # Write the updated signals array to file
    with open(log_file, 'w') as f:
        json.dump(signals, f, indent=2)
    
    logger.info(f"Signal {signal['id']} ({signal['type']}) for {signal['symbol']} successfully logged to file")
    
    return log_file

async def send_signal_to_webhook(signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send the signal to a webhook if configured"""
    if not WEBHOOK_URL:
        logger.info("No webhook URL configured, skipping webhook dispatch")
        return None
    
    logger.info(f"Sending signal ID {signal['id']} to webhook: {WEBHOOK_URL}")
    
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Making POST request to webhook")
            response = await client.post(WEBHOOK_URL, json=signal)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Signal ID {signal['id']} successfully sent to webhook")
            return result
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from webhook: {e} (Status code: {e.response.status_code})")
        logger.error(f"Response content: {e.response.text}")
        return {"error": str(e), "status_code": e.response.status_code}
    except Exception as e:
        logger.error(f"Error sending signal to webhook: {str(e)}", exc_info=True)
        return {"error": str(e)}

def format_signal_for_human(signal: Dict[str, Any]) -> str:
    """Format the signal for human-readable output"""
    logger.info(f"Formatting signal ID {signal['id']} for human-readable output")
    
    signal_type = signal["type"]
    
    if signal_type == "none" or signal.get("status") == "no_signal":
        logger.info("No actionable signal to format")
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
        logger.debug(f"Processing stub pattern: {pattern_type} with confidence {pattern_strength}%")
    else:
        pattern_strength = pattern.get("strength", 0)
        pattern_description = ""
        logger.debug(f"Processing detected pattern: {pattern_type} with strength {pattern_strength}")
    
    # Calculate potential profit/loss
    if signal_type == "BUY":
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
        logger.debug(f"BUY signal risk: {risk}, reward: {reward}")
    else:  # SELL
        risk = stop_loss - entry_price
        reward = entry_price - take_profit
        logger.debug(f"SELL signal risk: {risk}, reward: {reward}")
    
    risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
    logger.debug(f"Risk/reward ratio calculated: 1:{risk_reward_ratio}")
    
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
    
    logger.info(f"Formatted human-readable signal for {symbol}: {signal_type} signal")
    return message

def format_messaging_signal(signal: Dict[str, Any]) -> str:
    """Format signal for messaging platform in the requested format"""
    logger.info(f"Formatting signal ID {signal['id']} for messaging")
    
    signal_type = signal["type"]
    
    if signal_type == "none" or signal.get("status") == "no_signal":
        logger.info("No actionable signal to format for messaging")
        return "NO SIGNAL GENERATED"
    
    symbol = signal["symbol"]
    entry_price = signal["entry_price"]
    stop_loss = signal["stop_loss"]
    take_profit = signal["take_profit"]
    
    # Simple format as requested
    message = f"""SIGNAL ALERT: 
{signal_type}
Price: {entry_price}
SL: {stop_loss}
TP: {take_profit}"""
    
    # Print directly to stdout for clean terminal display
    print(f"\n=== MESSAGING SIGNAL ===\n{message}\n======================")
    
    return message

# Middleware to log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Received {request.method} request at {request.url.path}")
    response = await call_next(request)
    logger.info(f"Returning response with status code: {response.status_code}")
    return response

# Define API endpoints
@app.post("/dispatch")
async def dispatch_signal(signal: TradingSignal):
    """
    Dispatch a trading signal to various outputs (file log, webhook, etc.)
    """
    logger.info(f"Received signal for dispatch: {signal.id} - {signal.type} for {signal.symbol}")
    logger.debug(f"Full signal data: {signal.json()}")
    
    try:
        # Convert Pydantic model to dict
        signal_dict = signal.dict()
        
        # Format signal for human-readable output
        logger.info("STEP 1: Formatting signal for human-readable output")
        human_readable = format_signal_for_human(signal_dict)
        
        # Format signal for messaging platform and print to terminal
        logger.info("STEP 2: Formatting signal for messaging platform")
        messaging_signal = format_messaging_signal(signal_dict)
        
        # Log to file
        logger.info("STEP 3: Logging signal to file")
        log_file = log_signal_to_file(signal_dict)
        
        # Send to webhook if configured
        logger.info("STEP 4: Sending signal to webhook (if configured)")
        webhook_result = await send_signal_to_webhook(signal_dict)
        
        logger.info(f"Signal {signal.id} dispatched successfully to all configured outputs")
        
        # Return a simple response
        return {
            "status": "success",
            "message": "Signal dispatched successfully"
        }
        
    except Exception as e:
        error_msg = f"Error dispatching signal {signal.id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check endpoint called")
    return {"status": "healthy", "service": "signal_dispatcher"}

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Signal dispatcher service is ready to receive requests") 