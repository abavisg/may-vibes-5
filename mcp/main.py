import json
import logging
import os
import sys
import traceback
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the ServiceLogger
from utils.logging_utils import ServiceLogger

# Initialize the logger for the MCP service
logger = ServiceLogger("mcp").get_logger()

# Log uncaught exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

# Configuration
PATTERN_DETECTOR_URL = os.getenv("PATTERN_DETECTOR_URL", "http://localhost:8001/detect")
SIGNAL_GENERATOR_URL = os.getenv("SIGNAL_GENERATOR_URL", "http://localhost:8002/generate")
SIGNAL_DISPATCHER_URL = os.getenv("SIGNAL_DISPATCHER_URL", "http://localhost:8003/dispatch")

app = FastAPI(
    title="MCP Server",
    description="Model Context Protocol for orchestrating the signal pipeline",
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

class Candle(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    type_of_data: str

async def call_pattern_detector(candle: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(PATTERN_DETECTOR_URL, json=candle)
        return response.json()

async def call_signal_generator(pattern_detection: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(SIGNAL_GENERATOR_URL, json=pattern_detection)
        return response.json()

async def call_signal_dispatcher(signal: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(SIGNAL_DISPATCHER_URL, json=signal)
        return response.json()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    response = await call_next(request)
    return response

@app.post("/mcp/candle")
async def receive_candle(candle: Candle):
    logger.info(f"[START] /mcp/candle for {candle.symbol} at {candle.timestamp}")
    logger.info(f"Input: {candle.dict()}")
    try:
        candle_dict = candle.dict()
        pattern_detection_payload_for_signal_generator: Dict[str, Any]
        actual_pattern_detection_result = await call_pattern_detector(candle_dict)
        pattern_detection_payload_for_signal_generator = actual_pattern_detection_result
        patterns = actual_pattern_detection_result.get("patterns", [])
        proceed_to_signal_generation = bool(patterns and len(patterns) > 0)
        if proceed_to_signal_generation:
            signal = await call_signal_generator(pattern_detection_payload_for_signal_generator)
            if isinstance(signal, dict) and signal.get("status") == "no_signal":
                logger.info(f"Output: No actionable signal generated for {candle.symbol}")
                logger.info(f"[END] /mcp/candle for {candle.symbol} at {candle.timestamp}")
                return {
                    "status": "success",
                    "message": "Pattern detected but no signal generated",
                    "pattern_detection": pattern_detection_payload_for_signal_generator
                }
            dispatch_result = await call_signal_dispatcher(signal)
            logger.info(f"Output: {dispatch_result}")
            logger.info(f"[END] /mcp/candle for {candle.symbol} at {candle.timestamp}")
            return {
                "status": "success",
                "message": "Signal processed and dispatched",
                "pattern_detection": pattern_detection_payload_for_signal_generator,
                "signal": signal,
                "dispatch_result": dispatch_result
            }
        else:
            logger.info(f"Output: No patterns detected, no signal generated for {candle.symbol}")
            logger.info(f"[END] /mcp/candle for {candle.symbol} at {candle.timestamp}")
            return {
                "status": "success",
                "message": "No patterns detected, no signal generated",
                "pattern_detection": pattern_detection_payload_for_signal_generator
            }
    except Exception as e:
        logger.error(f"Error processing candle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing candle: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "service": "mcp",
        "dependencies": {
            "pattern_detector": "unknown",
            "signal_generator": "unknown",
            "signal_dispatcher": "unknown"
        }
    }

@app.on_event("startup")
async def startup_event():
    logger.info("MCP service started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("MCP service stopped.") 