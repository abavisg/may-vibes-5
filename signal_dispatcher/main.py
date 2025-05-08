import json
import logging
import os
import sys # Import sys for StreamHandler
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the ServiceLogger
from utils.logging_utils import ServiceLogger

# Initialize the logger for the signal dispatcher service
logger = ServiceLogger("signal_dispatcher").get_logger()

SIGNAL_LOG_DIR = os.getenv("SIGNAL_LOG_DIR", "./signal_logs")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", None)

os.makedirs(SIGNAL_LOG_DIR, exist_ok=True)

app = FastAPI(
    title="Signal Dispatcher",
    description="Service to dispatch trading signals to various outputs",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
    type_of_data: str

def log_signal_to_file(signal: Dict[str, Any]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(SIGNAL_LOG_DIR, f"signals_{today}.json")
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r') as f:
                content = f.read().strip()
            if not content:
                signals = []
            else:
                try:
                    signals = json.loads(content)
                    if not isinstance(signals, list):
                        signals = [signals]
                except json.JSONDecodeError:
                    signals = []
        except Exception:
            signals = []
    else:
        signals = []
    signals.append(signal)
    with open(log_file, 'w') as f:
        json.dump(signals, f, indent=2)
    logger.info(f"Signal {signal['id']} ({signal['type']}) for {signal['symbol']} logged to {log_file}")
    return log_file

def format_signal_for_human(signal: Dict[str, Any]) -> str:
    signal_type = signal["type"]
    if signal_type == "none" or signal.get("status") == "no_signal":
        return "NO SIGNAL GENERATED"
    symbol = signal["symbol"]
    entry_price = signal["entry_price"]
    stop_loss = signal["stop_loss"]
    take_profit = signal["take_profit"]
    pattern = signal["pattern"]
    pattern_type = pattern.get("type", "unknown")
    pattern_strength = int(pattern.get("confidence", pattern.get("strength", 0)) * 100) if "confidence" in pattern or "strength" in pattern else 0
    pattern_description = pattern.get("description", "")
    risk = abs(entry_price - stop_loss) if entry_price and stop_loss else 0
    reward = abs(take_profit - entry_price) if take_profit and entry_price else 0
    risk_reward_ratio = round(reward / risk, 2) if risk > 0 else 0
    message = (
        f"========== SIGNAL ALERT | Symbol: {symbol} | Action: {signal_type} | Pattern: {pattern_type.upper()} (Strength: {pattern_strength}%) | "
        f"{pattern_description} | Entry: {entry_price} | Stop Loss: {stop_loss} | Take Profit: {take_profit} | "
        f"Risk/Reward: 1:{risk_reward_ratio} | Timestamp: {signal['timestamp']} | ID: {signal['id']} ============"
    )
    logger.info(message)
    return message

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    return response

@app.post("/dispatch")
async def dispatch_signal(signal: TradingSignal):
    logger.info(f"[START] /dispatch for {signal.id} - {signal.type} {signal.symbol}")
    logger.info(f"Input: {signal.dict()}")
    try:
        signal_dict = signal.dict()
        # Format and log user-friendly message
        format_signal_for_human(signal_dict)
        # Log to file
        log_signal_to_file(signal_dict)
        # (Optional) Send to webhook (not logged here)
        #logger.info(f"\n========\nSIGNAL ALERT |\n Symbol: {signal.symbol} |\n Action: {signal.type} |\n Pattern: {signal.pattern.get('type', 'unknown')} |\n Pattern Strength: {signal.pattern.get('confidence', signal.pattern.get('strength', 0)) * 100}% | Description: {signal.pattern.get('description', '')} |\n Entry: {signal.entry_price} |\n Stop Loss: {signal.stop_loss} |\n Take Profit: {signal.take_profit} |\n Timestamp: {signal.timestamp} |\n ID: {signal.id}\n========")
        
        logger.info(f"Output: Signal dispatched successfully for {signal.id}")
        logger.info(f"[END] /dispatch for {signal.id} - {signal.type} {signal.symbol}")
        return {
            "status": "success",
            "message": "Signal dispatched successfully"
        }
    except Exception as e:
        logger.error(f"Error dispatching signal {signal.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error dispatching signal {signal.id}: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "signal_dispatcher"}

@app.on_event("startup")
async def startup_event():
    logger.info("Signal dispatcher service started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Signal dispatcher service stopped.")

@app.get("/signals")
async def get_latest_signals():
    """
    Fetch the 100 most recent signals across all log files
    """
    try:
        all_signals = []
        files = os.listdir(SIGNAL_LOG_DIR)
        signal_files = [f for f in files if f.startswith("signals_") and f.endswith(".json")]
        
        # Sort files by date (newest first)
        signal_files.sort(reverse=True)
        
        # Read signals from files until we have 100 or run out of files
        for file_name in signal_files:
            file_path = os.path.join(SIGNAL_LOG_DIR, file_name)
            try:
                with open(file_path, 'r') as f:
                    file_signals = json.load(f)
                    all_signals.extend(file_signals)
                    if len(all_signals) >= 100:
                        break
            except Exception as e:
                logger.error(f"Error reading signal file {file_path}: {str(e)}")
        
        # Limit to 100 signals, sorted by timestamp (newest first)
        all_signals = sorted(
            all_signals[:100], 
            key=lambda s: s.get('timestamp', ''), 
            reverse=True
        )
        
        return all_signals
    except Exception as e:
        logger.error(f"Error fetching signals: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching signals: {str(e)}")

@app.get("/signals/{date}")
async def get_signals_by_date(date: str):
    """
    Fetch signals for a specific date (format: YYYY-MM-DD)
    """
    try:
        # Validate date format
        datetime.strptime(date, "%Y-%m-%d")
        
        log_file = os.path.join(SIGNAL_LOG_DIR, f"signals_{date}.json")
        if not os.path.exists(log_file):
            return []
            
        with open(log_file, 'r') as f:
            signals = json.load(f)
            
        # Sort by timestamp (newest first)
        signals = sorted(
            signals, 
            key=lambda s: s.get('timestamp', ''), 
            reverse=True
        )
            
        return signals
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error fetching signals for date {date}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching signals: {str(e)}") 