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
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
MCP_URL = os.getenv("MCP_URL", "http://localhost:8000/mcp/candle")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "30"))  # seconds
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
USE_MOCK_DATA = TWELVE_DATA_API_KEY is None or os.getenv("FORCE_MOCK_DATA", "false").lower() == "true"  # Use mock data if API key is not provided or FORCE_MOCK_DATA is true
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() == "true"  # Use stub signal generators

# Import external candle generator
from poller.candle_generator import generate_candle

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
    try:
        if data.get("status") != "ok" or not data.get("values"):
            logger.error(f"Invalid Twelve Data response: {data}")
            return None
        
        # Get the most recent candle data
        candle_data = data["values"][0]
        
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
        
        return candle
    except Exception as e:
        logger.error(f"Error transforming Twelve Data response: {e}")
        return None

async def get_real_candle() -> Optional[Dict]:
    """Fetch real candle data from Twelve Data API"""
    if not TWELVE_DATA_API_KEY:
        logger.warning("Twelve Data API key not provided, cannot fetch real candle data")
        return None
    
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1min&apikey={TWELVE_DATA_API_KEY}&format=JSON&dp=3"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Twelve Data API response: {json.dumps(data)}")
            
            candle = transform_twelve_data_response(data)
            if candle:
                logger.info(f"Successfully fetched real candle data: {json.dumps(candle)}")
                return candle
            else:
                logger.error("Failed to transform Twelve Data response")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching real candle data: {str(e)}")
        return None

async def poll_and_send():
    """Main polling function to fetch candles and send to MCP"""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Get candle data (real or mock)
                candle = None
                
                if not USE_MOCK_DATA:
                    candle = await get_real_candle()
                
                # Fall back to external candle generator if real data fetch failed
                if candle is None:
                    if USE_MOCK_DATA:
                        logger.info("Using external candle generator")
                    else:
                        logger.warning("Failed to get real candle data, falling back to external candle generator")
                    
                    # Use the external candle generator
                    candle = generate_candle()
                
                logger.info(f"Candle data: {json.dumps(candle)}")
                
                # Send to MCP server
                response = await client.post(MCP_URL, json=candle)
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent candle to MCP: {response.text}")
                else:
                    logger.error(f"Failed to send candle to MCP. Status: {response.status_code}, Response: {response.text}")
                
                # Wait for the specified interval
                await asyncio.sleep(POLLING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {str(e)}")
                await asyncio.sleep(5)  # Wait a bit before retrying after an error

async def main():
    """Main entry point"""
    logger.info("Starting XAUUSD Candle Poller Service")
    logger.info(f"MCP URL: {MCP_URL}")
    logger.info(f"Polling interval: {POLLING_INTERVAL} seconds")
    logger.info(f"Using external candle generator: {USE_MOCK_DATA}")
    logger.info(f"Using signal stubs: {USE_SIGNAL_STUBS}")
    
    await poll_and_send()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Poller service stopped by user") 