import asyncio
import datetime
import json
import logging
import os
import random
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [poller] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Poller service starting up")

# Configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp/candle")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "3"))  # seconds
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
USE_MOCK_DATA = TWELVE_DATA_API_KEY is None or os.getenv("FORCE_MOCK_DATA", "false").lower() == "true"  # Use mock data if API key is not provided or FORCE_MOCK_DATA is true
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() == "true"  # Use stub signal generators

logger.info(f"Configuration loaded:")
logger.info(f"MCP_URL: {MCP_URL}")
logger.info(f"POLLING_INTERVAL: {POLLING_INTERVAL} seconds")
logger.info(f"TWELVE_DATA_API_KEY: {'Set' if TWELVE_DATA_API_KEY else 'Not set'}")
logger.info(f"USE_MOCK_DATA: {USE_MOCK_DATA}")
logger.info(f"USE_SIGNAL_STUBS: {USE_SIGNAL_STUBS}")

# Import external candle generator
from poller.candle_generator import generate_candle
logger.info("Imported external candle generator")

def transform_twelve_data_response(data: Dict) -> Dict:
    """
    Transform Twelve Data API response into our candle format
    
    Example Twelve Data response:
    {
        "meta": {
            "symbol": "XAU/USD",
            "interval": "1min",
            "currency": "USD",
            "exchange_timezone": "UTC",
            "exchange": "FOREX",
            "type": "Physical Currency"
        },
        "values": [
            {
                "datetime": "2023-05-10 12:23:00",
                "open": "2032.54004",
                "high": "2032.84998",
                "low": "2032.22998",
                "close": "2032.31995",
                "volume": "1234"
            }
        ],
        "status": "ok"
    }
    """
    logger.debug(f"Transforming Twelve Data response: {json.dumps(data)}")
    
    try:
        if data.get("status") != "ok" or not data.get("values"):
            logger.error(f"Invalid Twelve Data response: {data}")
            return None
        
        # Get the most recent candle data
        candle_data = data["values"][0]
        logger.debug(f"Processing candle data: {json.dumps(candle_data)}")
        
        # Create our candle format
        candle = {
            "symbol": data["meta"]["symbol"],
            "timestamp": candle_data["datetime"],
            "open": float(candle_data["open"]),
            "high": float(candle_data["high"]),
            "low": float(candle_data["low"]),
            "close": float(candle_data["close"]),
            "volume": int(candle_data["volume"]) if candle_data.get("volume") else 0
        }
        
        logger.info(f"Successfully transformed Twelve Data response for {candle['symbol']} at {candle['timestamp']}")
        return candle
    except Exception as e:
        logger.error(f"Error transforming Twelve Data response: {e}", exc_info=True)
        return None

async def get_real_candle() -> Optional[Dict]:
    """Fetch real candle data from Twelve Data API"""
    if not TWELVE_DATA_API_KEY:
        logger.warning("Twelve Data API key not provided, cannot fetch real candle data")
        return None
    
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1min&apikey={TWELVE_DATA_API_KEY}&format=JSON&dp=3"
        logger.info(f"Fetching real candle data from Twelve Data API for XAU/USD")
        logger.debug(f"API URL: {url}")
        
        async with httpx.AsyncClient() as client:
            logger.debug("Sending request to Twelve Data API")
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            logger.debug("Successfully received response from Twelve Data API")
            
            candle = transform_twelve_data_response(data)
            if candle:
                logger.info(f"Successfully fetched real XAU/USD candle data at {candle['timestamp']}")
                return candle
            else:
                logger.error("Failed to transform Twelve Data response")
                return None
                
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from Twelve Data API: {e} (Status code: {e.response.status_code})")
        logger.error(f"Response content: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error fetching real candle data: {str(e)}", exc_info=True)
        return None

async def poll_and_send():
    """Main polling function to fetch candles and send to MCP"""
    logger.info("Starting polling loop")
    poll_count = 0
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                poll_count += 1
                logger.info(f"Poll #{poll_count} started")
                
                # Get candle data (real or mock)
                candle = None
                
                if not USE_MOCK_DATA:
                    logger.info("Attempting to fetch real market data")
                    candle = await get_real_candle()
                
                # Fall back to external candle generator if real data fetch failed
                if candle is None:
                    if USE_MOCK_DATA:
                        logger.info("Using external candle generator (as configured)")
                    else:
                        logger.warning("Failed to get real candle data, falling back to external candle generator")
                    
                    # Use the external candle generator
                    logger.debug("Calling external candle generator")
                    candle = generate_candle()
                    logger.info(f"Generated mock candle data for {candle['symbol']} at {candle['timestamp']}")
                
                # Send to MCP server
                logger.info(f"Sending candle data to MCP for {candle['symbol']} at {candle['timestamp']}")
                logger.debug(f"Full candle data: {json.dumps(candle)}")
                
                logger.debug(f"Making POST request to {MCP_URL}")
                response = await client.post(MCP_URL, json=candle)
                
                if response.status_code == 200:
                    result = response.json()
                    message = result.get("message", "No message")
                    logger.info(f"Successfully sent candle to MCP. Response: {message}")
                    logger.debug(f"Full MCP response: {response.text}")
                else:
                    logger.error(f"Failed to send candle to MCP. Status: {response.status_code}")
                    logger.error(f"Response: {response.text}")
                
                logger.info(f"Poll #{poll_count} completed, waiting {POLLING_INTERVAL} seconds for next poll")
                # Wait for the specified interval
                await asyncio.sleep(POLLING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}", exc_info=True)
                logger.info(f"Retrying in 5 seconds...")
                await asyncio.sleep(5)  # Wait a bit before retrying after an error

async def main():
    """Main entry point"""
    logger.info("=== XAUUSD Candle Poller Service ===")
    logger.info(f"MCP URL: {MCP_URL}")
    logger.info(f"Polling interval: {POLLING_INTERVAL} seconds")
    logger.info(f"Using mock data: {USE_MOCK_DATA}")
    logger.info(f"Using signal stubs: {USE_SIGNAL_STUBS}")
    
    logger.info("Starting polling loop...")
    await poll_and_send()

if __name__ == "__main__":
    try:
        logger.info("Initializing poller service")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Poller service stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled exception in poller service: {str(e)}", exc_info=True) 