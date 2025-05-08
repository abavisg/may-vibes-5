import asyncio
import logging
import os
import time # Import time for measuring duration
import sys # Import sys for StreamHandler
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from poller.candle_generator import generate_dummy_candles

# Load environment variables
load_dotenv()

# Import the ServiceLogger
from utils.logging_utils import ServiceLogger

# Initialize the logger for the poller service
logger = ServiceLogger("poller").get_logger()

# Configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp/candle")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "10"))  # seconds
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() in ("true", "1", "yes")
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "twelvedata").lower()

app = FastAPI(
    title="Poller Service",
    description="Service for polling market data and sending to MCP",
    version="0.1.0"
)

poller_running = False
poller_task = None
last_candle = None

# --- Provider registry ---
PROVIDERS = {}
PARSERS = {}

# Import providers and parsers dynamically
try:
    from poller.data_providers import twelvedata, finnhub
    from poller.parsers import twelvedata as twelvedata_parser, finnhub as finnhub_parser
    PROVIDERS["twelvedata"] = twelvedata
    PROVIDERS["finnhub"] = finnhub
    PARSERS["twelvedata"] = twelvedata_parser
    PARSERS["finnhub"] = finnhub_parser
except ImportError as e:
    logger.warning(f"Could not import all data providers/parsers: {e}")

async def fetch_candle(symbol: str = "XAU/USD") -> Optional[Dict]:
    logger.info(f"Attempting to fetch candle from {DATA_PROVIDER} provider for {symbol}")
    provider = PROVIDERS.get(DATA_PROVIDER)
    parser = PARSERS.get(DATA_PROVIDER)
    if provider and parser:
        try:
            start_time = time.time()
            raw = await provider.fetch_candle(symbol)
            end_time = time.time()
            logger.info(f"Successfully fetched raw data from {DATA_PROVIDER} in {end_time - start_time:.4f} seconds.")
            
            start_time = time.time()
            candle = parser.parse_candle_response(raw)
            end_time = time.time()
            logger.info(f"Successfully parsed candle data in {end_time - start_time:.4f} seconds.")
            
            if candle:
                logger.info(f"Fetched and parsed candle for {symbol} at {candle.get('timestamp')}")
                return candle
            else:
                logger.error(f"Could not parse response from {DATA_PROVIDER}: {raw}")
                return None
        except ValueError as e:
            logger.error(f"{DATA_PROVIDER} provider configuration or data error: {e}")
            return None
        except Exception as e:
            logger.error(f"{DATA_PROVIDER} provider failed during fetch or parse: {e}")
            return None
    else:
        logger.error(f"Data provider '{DATA_PROVIDER}' or its parser not found")
        return None

async def fetch_and_process_candle():
    """Helper function to fetch candle data and send it to MCP"""
    logger.info("[PROCESS] Starting candle fetch and process cycle")
    try:
        candle = None
        if USE_SIGNAL_STUBS:
            logger.info("[PROCESS] Using dummy candle data")
            candle = generate_dummy_candles()
        else:
            logger.info("[PROCESS] Attempting to fetch live/test candle data")
            candle = await fetch_candle()

        if candle is None:
            logger.error("[PROCESS] Failed to fetch candle data. Skipping MCP dispatch.")
            return None, None
        
        # Ensure timestamp is a string for MCP (Pydantic validation)
        if isinstance(candle.get("timestamp"), (int, float)):
            candle["timestamp"] = str(int(candle["timestamp"]))
        
        logger.info(f"[PROCESS] Sending candle to MCP: {candle.get('symbol')} at {candle.get('timestamp')}")
        start_time = time.time()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(MCP_URL, json=candle)
            end_time = time.time()
            logger.info(f"[PROCESS] Received response from MCP (Status: {response.status_code}) in {end_time - start_time:.4f} seconds.")
            logger.debug(f"[PROCESS] MCP Response: {response.text}") # Use debug for potentially long response
            return candle, response
    except httpx.TimeoutException as e:
        logger.error(f"[PROCESS] Timeout when sending candle to MCP: {e}")
        return None, None
    except Exception as e:
        logger.error(f"[PROCESS] Error in fetch_and_process_candle: {str(e)}")
        # Re-raise to be caught by the polling loop's error handling
        raise

async def poll_and_send():
    logger.info("Starting poller background task loop")
    global poller_running, last_candle
    poll_count = 0
    while poller_running:
        poll_count += 1
        logger.info(f"--- Polling Cycle {poll_count} ---")
        try:
            candle, response = await fetch_and_process_candle()
            if candle is not None:
                last_candle = candle
            logger.info(f"--- End of Polling Cycle {poll_count} ---")
        except Exception as e:
            logger.error(f"Unhandled error during polling cycle {poll_count}: {str(e)}")
            # Decide whether to continue or stop the poller based on the error
            # For now, we'll just log and wait.
        
        logger.info(f"Waiting for {POLLING_INTERVAL} seconds before next poll...")
        await asyncio.sleep(POLLING_INTERVAL)

async def start_poller_background():
    logger.info("Checking if poller background task should start.")
    global poller_running, poller_task
    if poller_running:
        logger.info("Poller background task is already running.")
        return
    logger.info("Starting new poller background task.")
    poller_running = True
    poller_task = asyncio.create_task(poll_and_send())

@app.on_event("startup")
async def startup_event():
    logger.info("Poller service startup initiated.")
    await start_poller_background()
    logger.info("Poller service startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    global poller_running, poller_task
    logger.info("Poller service shutdown initiated.")
    poller_running = False
    if poller_task:
        logger.info("Cancelling poller background task.")
        poller_task.cancel()
        try:
            await poller_task
            logger.info("Poller background task cancelled successfully.")
        except asyncio.CancelledError:
            logger.info("Poller background task confirmed cancelled.")
        except Exception as e:
            logger.error(f"Error during poller task cancellation: {str(e)}")
    logger.info("Poller service shutdown complete.")

@app.get("/health")
async def health_check():
    logger.info("Health check requested for Poller service.")
    health_status = {
        "status": "healthy",
        "service": "poller",
        "poller_running": poller_running,
        "last_candle_time": last_candle["timestamp"] if last_candle else None,
        "config": {
            "polling_interval": POLLING_INTERVAL,
            "data_provider": DATA_PROVIDER
        },
        "task_status": "running" if poller_task and not poller_task.done() else "stopped"
    }
    logger.info(f"Health check response: {health_status}")
    return health_status

@app.get("/last-candle")
async def get_last_candle():
    logger.info("Last candle requested.")
    if last_candle:
        logger.info(f"Returning last candle for {last_candle.get('symbol')}")
        return last_candle
    else:
        logger.info("No last candle available.")
        return {"status": "no_data", "message": "No candle data has been processed yet"}

@app.post("/trigger-poll")
async def trigger_poll():
    logger.info("Manual poll triggered.")
    try:
        candle, response = await fetch_and_process_candle()
        
        if response and response.status_code == 200:
            result = response.json()
            logger.info("Manual poll successful.")
            return {
                "status": "success",
                "message": "Manual poll successful",
                "candle": candle,
                "mcp_response": result
            }
        else:
            error_message = f"MCP returned status {response.status_code}" if response else "No response from MCP"
            logger.error(f"Manual poll failed: {error_message}")
            return {
                "status": "error",
                "message": f"Manual poll failed: {error_message}",
                "candle": candle
            }
    except Exception as e:
        logger.error(f"Error performing manual poll: {str(e)}")
        return {
            "status": "error",
            "message": f"Error performing manual poll: {str(e)}"
        }

if __name__ == "__main__":
    try:
        logger.info("Poller service starting via uvicorn.")
        uvicorn.run(app, host="0.0.0.0", port=8004)
    except KeyboardInterrupt:
        logger.info("Poller service stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Unhandled exception during uvicorn run: {str(e)}")