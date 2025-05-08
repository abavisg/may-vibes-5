import logging
import os
import sys # Import sys for StreamHandler
from typing import Dict, Any, Optional # Import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
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

        # Check if type_of_data is present and not None
        type_of_data = candle.get("type_of_data")
        if type_of_data is None:
            logger.error("type_of_data is missing in the incoming candle data.")
            raise HTTPException(status_code=400, detail="type_of_data field is required in candle data")

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
            # Use the retrieved type_of_data (guaranteed not None by the check above)
            "type_of_data": type_of_data,
            "pattern": pattern
        }
        logger.info(f"Output: {signal}")
        logger.info(f"[END] /generate for {candle.get('symbol', 'unknown')} at {candle.get('timestamp', 'unknown')}")
        return signal
    except HTTPException as e:
        # Re-raise HTTPException to be handled by FastAPI
        raise e
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