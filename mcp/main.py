import json
import logging
import os
from typing import Dict, Any

import httpx
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

# Configuration
PATTERN_DETECTOR_URL = os.getenv("PATTERN_DETECTOR_URL", "http://localhost:8001/detect")
SIGNAL_GENERATOR_URL = os.getenv("SIGNAL_GENERATOR_URL", "http://localhost:8002/generate")
SIGNAL_DISPATCHER_URL = os.getenv("SIGNAL_DISPATCHER_URL", "http://localhost:8003/dispatch")

# Create FastAPI application
app = FastAPI(
    title="MCP Server",
    description="Main Control Program for orchestrating the signal pipeline",
    version="0.1.0"
)

# Define request models
class Candle(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

# Define helper functions
async def call_pattern_detector(candle: Dict[str, Any]) -> Dict[str, Any]:
    """Call the pattern detector service with the given candle data"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(PATTERN_DETECTOR_URL, json=candle)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from pattern detector: {e}")
            raise HTTPException(status_code=502, detail=f"Pattern detector service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling pattern detector: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error calling pattern detector: {str(e)}")

async def call_signal_generator(pattern_data: Dict[str, Any], candle: Dict[str, Any]) -> Dict[str, Any]:
    """Call the signal generator service with pattern and candle data"""
    payload = {
        "pattern": pattern_data,
        "candle": candle
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SIGNAL_GENERATOR_URL, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from signal generator: {e}")
            raise HTTPException(status_code=502, detail=f"Signal generator service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling signal generator: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error calling signal generator: {str(e)}")

async def call_signal_dispatcher(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Call the signal dispatcher service with the generated signal"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(SIGNAL_DISPATCHER_URL, json=signal)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from signal dispatcher: {e}")
            raise HTTPException(status_code=502, detail=f"Signal dispatcher service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling signal dispatcher: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error calling signal dispatcher: {str(e)}")

# Define API endpoints
@app.post("/mcp/candle")
async def receive_candle(candle: Candle):
    """
    Receive a candle from the poller service and orchestrate the signal pipeline
    """
    logger.info(f"Received candle: {candle.json()}")
    
    try:
        # Convert Pydantic model to dict
        candle_dict = candle.dict()
        
        # Step 1: Call pattern detector
        pattern_result = await call_pattern_detector(candle_dict)
        logger.info(f"Pattern detector result: {pattern_result}")
        
        # Step 2: If a pattern is detected (not neutral), proceed to signal generation
        pattern_type = pattern_result.get("pattern", "neutral")
        if pattern_type != "neutral":
            # Step 3: Generate signal based on pattern
            signal = await call_signal_generator(pattern_result, candle_dict)
            logger.info(f"Generated signal: {signal}")
            
            # Step 4: Dispatch the signal
            dispatch_result = await call_signal_dispatcher(signal)
            logger.info(f"Signal dispatch result: {dispatch_result}")
            
            return {
                "status": "success",
                "message": "Signal processed and dispatched",
                "pattern": pattern_result,
                "signal": signal,
                "dispatch_result": dispatch_result
            }
        else:
            return {
                "status": "success",
                "message": "No pattern detected, no signal generated",
                "pattern": pattern_result
            }
            
    except Exception as e:
        logger.error(f"Error processing candle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing candle: {str(e)}")

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "mcp"} 