"""
TwelveData API provider for market data.
"""
import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")
BASE_URL = "https://api.twelvedata.com"

async def fetch_candle(symbol: str = "XAU/USD") -> Dict[str, Any]:
    """Fetch the latest candle data from TwelveData API."""
    if not API_KEY:
        logger.warning("TwelveData API key not found in environment variables")
        raise ValueError("TwelveData API key not configured")
    
    url = f"{BASE_URL}/time_series"
    params = {
        "symbol": symbol,
        "interval": "5min",
        "outputsize": "1",
        "timezone": "UTC",
        "format": "json",
        "apikey": API_KEY
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching data from TwelveData: {e}")
        raise 