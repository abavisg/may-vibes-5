import asyncio
import datetime
import json
import logging
import os
import random
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

# Configure minimal logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [poller] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp/candle")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "5"))  # seconds
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
USE_MOCK_DATA = TWELVE_DATA_API_KEY is None
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS")

from poller.candle_generator import generate_candle

app = FastAPI(
    title="Poller Service",
    description="Service for polling market data and sending to MCP",
    version="0.1.0"
)

poller_running = False
poller_task = None
last_candle = None

def transform_twelve_data_response(data: Dict) -> Dict:
    try:
        if data.get("status") != "ok" or not data.get("values"):
            return None
        candle_data = data["values"][0]
        candle = {
            "symbol": data["meta"]["symbol"],
            "timestamp": candle_data["datetime"],
            "open": float(candle_data["open"]),
            "high": float(candle_data["high"]),
            "low": float(candle_data["low"]),
            "close": float(candle_data["close"]),
            "volume": int(candle_data["volume"]) if candle_data.get("volume") else 0
        }
        return candle
    except Exception:
        return None

async def get_real_candle() -> Optional[Dict]:
    if not TWELVE_DATA_API_KEY:
        return None
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1min&apikey={TWELVE_DATA_API_KEY}&format=JSON&dp=3"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            candle = transform_twelve_data_response(data)
            if candle:
                return candle
            else:
                return None
    except Exception:
        return None

async def poll_and_send():
    global poller_running, last_candle
    poll_count = 0
    async with httpx.AsyncClient() as client:
        while poller_running:
            try:
                poll_count += 1
                # Get candle data (real or mock)
                candle = None
                if not USE_MOCK_DATA:
                    candle = await get_real_candle()
                if candle is None:
                    candle = generate_candle()
                last_candle = candle
                logger.info(f"[POLL] Input: {candle}")
                response = await client.post(MCP_URL, json=candle)
                logger.info(f"[POLL] Output: {response.text}")
                await asyncio.sleep(POLLING_INTERVAL)
            except Exception as e:
                await asyncio.sleep(5)

async def start_poller_background():
    global poller_running, poller_task
    if poller_running:
        return
    poller_running = True
    poller_task = asyncio.create_task(poll_and_send())

@app.on_event("startup")
async def startup_event():
    logger.info("Poller service started.")
    await start_poller_background()

@app.on_event("shutdown")
async def shutdown_event():
    global poller_running, poller_task
    logger.info("Poller service stopped.")
    poller_running = False
    if poller_task:
        try:
            poller_task.cancel()
            await asyncio.wait_for(poller_task, timeout=5.0)
        except Exception:
            pass

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "poller",
        "poller_running": poller_running,
        "last_candle_time": last_candle["timestamp"] if last_candle else None,
        "config": {
            "polling_interval": POLLING_INTERVAL,
            "using_mock_data": USE_MOCK_DATA
        }
    }

@app.get("/last-candle")
async def get_last_candle():
    if last_candle:
        return last_candle
    else:
        return {"status": "no_data", "message": "No candle data has been processed yet"}

@app.post("/trigger-poll")
async def trigger_poll():
    try:
        candle = None
        if not USE_MOCK_DATA:
            candle = await get_real_candle()
        if candle is None:
            candle = generate_candle()
        logger.info(f"[TRIGGER] Input: {candle}")
        async with httpx.AsyncClient() as client:
            response = await client.post(MCP_URL, json=candle)
            logger.info(f"[TRIGGER] Output: {response.text}")
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "message": "Manual poll successful",
                    "candle": candle,
                    "mcp_response": result
                }
            else:
                return {
                    "status": "error",
                    "message": f"MCP returned status {response.status_code}",
                    "candle": candle
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error performing manual poll: {str(e)}"
        }

if __name__ == "__main__":
    try:
        logger.info("Poller service started.")
        uvicorn.run(app, host="0.0.0.0", port=8004)
    except KeyboardInterrupt:
        logger.info("Poller service stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled exception in poller service: {str(e)}") 