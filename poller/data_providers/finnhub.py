"""
Finnhub API provider for market data.
"""
import os
import httpx
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

API_KEY = os.getenv("FINNHUB_API_KEY", "")
BASE_URL = "https://finnhub.io/api/v1"

async def fetch_candle(symbol: str = "XAU/USD") -> Dict[str, Any]:
    """Fetch the latest candle data from Finnhub API."""
    if not API_KEY:
        logger.warning("Finnhub API key not found in environment variables")
        raise ValueError("Finnhub API key not configured")
    
    # Finnhub uses different symbols, let's handle common conversions
    symbol_map = {
        "XAU/USD": "OANDA:XAU_USD",  # Gold to USD
    #    "EUR/USD": "OANDA:EUR_USD",   # Euro to USD
        # Add more mappings as needed
    }
    
    # Use the mapped symbol or the original if no mapping exists
    finnhub_symbol = symbol_map.get(symbol, symbol)
    
    # Calculate time range for last minute candle
    now = datetime.now()
    end_time = int(now.timestamp())
    start_time = int((now - timedelta(minutes=5)).timestamp())  # Get last 5 minutes for safety
    
    url = f"{BASE_URL}/stock/candle"
    params = {
        "symbol": finnhub_symbol,
        "resolution": "1",  # 1 minute
        "from": start_time,
        "to": end_time,
        "token": API_KEY
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching data from Finnhub: {e}")
        raise 