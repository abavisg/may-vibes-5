import asyncio
import logging
import os
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
from poller.candle_generator import generate_candle

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
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS")
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
    logging.info(f"Fetching candle from {DATA_PROVIDER} provider")
    provider = twelvedata #PROVIDERS.get(DATA_PROVIDER)
    parser = twelvedata_parser #PARSERS.get(DATA_PROVIDER)
    if provider and parser:
        try:
            raw = await provider.fetch_candle(symbol)
            candle = parser.parse_candle_response(raw)
            if candle:
                return candle
        except Exception as e:
            logger.warning(f"{DATA_PROVIDER} provider failed: {e}")
    
    # Fallback logic is disabled for now
    # Uncomment this section to enable fallback to other providers
    # for name, prov in PROVIDERS.items():
    #     if name == DATA_PROVIDER:
    #         continue
    #     try:
    #         raw = await prov.fetch_candle(symbol)
    #         candle = PARSERS[name].parse_candle_response(raw)
    #         if candle:
    #             logger.info(f"Fallback to {name} provider succeeded.")
    #             return candle
    #     except Exception as e:
    #         logger.warning(f"Fallback provider {name} failed: {e}")
    
    return None

async def fetch_and_process_candle():
    """Helper function to fetch candle data and send it to MCP"""
    try:
        candle = None
        if not USE_SIGNAL_STUBS:
            candle = await fetch_candle()
        if candle is None:
            candle = generate_candle()
        
        logger.info(f"[PROCESS] Input: {candle}")
        async with httpx.AsyncClient() as client:
            response = await client.post(MCP_URL, json=candle)
            logger.info(f"[PROCESS] Output: {response.text}")
            return candle, response
    except Exception as e:
        logger.error(f"Error in fetch_and_process_candle: {str(e)}")
        raise

async def poll_and_send():
    logging.info("Starting poller background task")
    global poller_running, last_candle
    poll_count = 0
    while poller_running:
        try:
            poll_count += 1
            candle, _ = await fetch_and_process_candle()
            last_candle = candle
            await asyncio.sleep(POLLING_INTERVAL)
        except Exception as e:
            logger.error(f"Error in poll_and_send: {str(e)}")
            await asyncio.sleep(5)

async def start_poller_background():
    logging.info("Starting poller background task")
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
            "data_provider": DATA_PROVIDER
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
        candle, response = await fetch_and_process_candle()
        
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