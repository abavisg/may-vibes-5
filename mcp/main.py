import json
import logging
import os
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [mcp] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("MCP service starting up")

# Configuration
PATTERN_DETECTOR_URL = os.getenv("PATTERN_DETECTOR_URL", "http://localhost:8001/detect")
SIGNAL_GENERATOR_URL = os.getenv("SIGNAL_GENERATOR_URL", "http://localhost:8002/generate")
SIGNAL_DISPATCHER_URL = os.getenv("SIGNAL_DISPATCHER_URL", "http://localhost:8003/dispatch")

# Feature flags
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() == "true"

logger.info(f"Service URLs configured:")
logger.info(f"PATTERN_DETECTOR_URL: {PATTERN_DETECTOR_URL}")
logger.info(f"SIGNAL_GENERATOR_URL: {SIGNAL_GENERATOR_URL}")
logger.info(f"SIGNAL_DISPATCHER_URL: {SIGNAL_DISPATCHER_URL}")
logger.info(f"USE_SIGNAL_STUBS: {USE_SIGNAL_STUBS}")

# Create FastAPI application
app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol for orchestrating the signal pipeline",
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
    logger.info(f"Sending candle data to pattern detector for {candle['symbol']} at {candle['timestamp']}")
    
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Making POST request to {PATTERN_DETECTOR_URL}")
            response = await client.post(PATTERN_DETECTOR_URL, json=candle)
            response.raise_for_status()
            result = response.json()
            
            # Log number of patterns detected
            patterns = result.get("patterns", [])
            logger.info(f"Pattern detector found {len(patterns)} patterns for {candle['symbol']}")
            
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from pattern detector: {e} (Status code: {e.response.status_code})")
            logger.error(f"Response content: {e.response.text}")
            raise HTTPException(status_code=502, detail=f"Pattern detector service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling pattern detector: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error calling pattern detector: {str(e)}")

async def call_signal_generator(pattern_detection: Dict[str, Any]) -> Dict[str, Any]:
    """Call the signal generator service with pattern detection data"""
    candle = pattern_detection.get("candle", {})
    symbol = candle.get("symbol", "unknown")
    timestamp = candle.get("timestamp", "unknown")
    
    logger.info(f"Sending pattern detection to signal generator for {symbol} at {timestamp}")
    
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Making POST request to {SIGNAL_GENERATOR_URL}")
            # The pattern detection already contains the candle data, so we can send it directly
            response = await client.post(SIGNAL_GENERATOR_URL, json=pattern_detection)
            response.raise_for_status()
            result = response.json()
            
            # Check if a signal was generated
            if isinstance(result, dict) and result.get("status") == "no_signal":
                logger.info(f"No signal generated for {symbol} at {timestamp}")
            else:
                signal_type = result.get("type", "unknown")
                logger.info(f"Signal generator produced {signal_type} signal for {symbol} at {timestamp}")
                
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from signal generator: {e} (Status code: {e.response.status_code})")
            logger.error(f"Response content: {e.response.text}")
            raise HTTPException(status_code=502, detail=f"Signal generator service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling signal generator: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error calling signal generator: {str(e)}")

async def call_signal_dispatcher(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Call the signal dispatcher service with the generated signal"""
    symbol = signal.get("symbol", "unknown")
    signal_type = signal.get("type", "unknown")
    signal_id = signal.get("id", "unknown")
    
    logger.info(f"Dispatching {signal_type} signal for {symbol} (ID: {signal_id})")
    
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Making POST request to {SIGNAL_DISPATCHER_URL}")
            response = await client.post(SIGNAL_DISPATCHER_URL, json=signal)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Signal dispatcher successfully processed signal ID: {signal_id}")
            return result
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from signal dispatcher: {e} (Status code: {e.response.status_code})")
            logger.error(f"Response content: {e.response.text}")
            raise HTTPException(status_code=502, detail=f"Signal dispatcher service error: {str(e)}")
        except Exception as e:
            logger.error(f"Error calling signal dispatcher: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error calling signal dispatcher: {str(e)}")

# Middleware to log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Received {request.method} request at {request.url.path}")
    response = await call_next(request)
    logger.info(f"Returning response with status code: {response.status_code}")
    return response

# Define API endpoints
@app.post("/mcp/candle")
async def receive_candle(candle: Candle):
    """
    Receive a candle from the poller service and orchestrate the signal pipeline
    """
    logger.info(f"Received candle from poller service: {candle.symbol} at {candle.timestamp}")
    logger.debug(f"Full candle data: {candle.json()}")
    
    try:
        # Convert Pydantic model to dict
        candle_dict = candle.dict()
        
        # Step 1: Call pattern detector
        logger.info(f"STEP 1: Calling pattern detector for {candle.symbol}")
        pattern_detection = await call_pattern_detector(candle_dict)
        
        # Get patterns from the response
        patterns = pattern_detection.get("patterns", [])
        
        # Step 2: Check if we should proceed to signal generation
        # Either we have patterns, or we're using signal stubs
        if patterns and len(patterns) > 0:
            pattern_types = [p.get("pattern", "unknown") for p in patterns]
            logger.info(f"STEP 2: Patterns detected ({', '.join(pattern_types)}), proceeding to signal generation")
            proceed_to_signal_generation = True
        elif USE_SIGNAL_STUBS:
            logger.info(f"STEP 2: No patterns detected, but USE_SIGNAL_STUBS=true, proceeding to signal generation anyway")
            proceed_to_signal_generation = True
        else:
            logger.info(f"No patterns detected for {candle.symbol}, stopping pipeline")
            proceed_to_signal_generation = False
            
        # Step 3: Generate signal if we should proceed
        if proceed_to_signal_generation:
            # Generate signal based on patterns or stubs
            logger.info(f"STEP 3: Calling signal generator for {candle.symbol}")
            signal = await call_signal_generator(pattern_detection)
            
            # Skip signal processing if "no_signal" status is returned
            if isinstance(signal, dict) and signal.get("status") == "no_signal":
                logger.info(f"No actionable signal generated for {candle.symbol}, stopping pipeline")
                return {
                    "status": "success",
                    "message": "Pattern detected but no signal generated",
                    "pattern_detection": pattern_detection
                }
            
            # Step 4: Dispatch the signal
            logger.info(f"STEP 4: Calling signal dispatcher for {signal.get('type', 'unknown')} signal")
            dispatch_result = await call_signal_dispatcher(signal)
            
            logger.info(f"Signal pipeline completed successfully for {candle.symbol}")
            return {
                "status": "success",
                "message": "Signal processed and dispatched",
                "pattern_detection": pattern_detection,
                "signal": signal,
                "dispatch_result": dispatch_result
            }
        else:
            return {
                "status": "success",
                "message": "No patterns detected, no signal generated",
                "pattern_detection": pattern_detection
            }
            
    except Exception as e:
        error_msg = f"Error processing candle: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check endpoint called")
    return {"status": "healthy", "service": "mcp"}

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Model Context Protocol service is ready to receive requests") 