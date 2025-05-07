"""
Parser for Finnhub API responses.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def parse_candle_response(response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Finnhub response into a standardized candle format."""
    try:
        # Check if response has expected structure and status
        if not response_data or "s" not in response_data or response_data["s"] != "ok":
            logger.warning("Invalid Finnhub response format or error status")
            return None
        
        # Check if all required data arrays are present
        required_keys = ["c", "h", "l", "o", "t", "v"]
        if not all(key in response_data for key in required_keys):
            logger.warning("Missing required fields in Finnhub response")
            return None
        
        # Get most recent data (last elements in arrays)
        if not response_data["t"] or len(response_data["t"]) == 0:
            logger.warning("No timestamps in Finnhub response")
            return None
        
        # Get the index of the last (most recent) candle
        idx = -1
        
        # Get symbol from response or use a default
        symbol = "UNKNOWN"
        if "symbol" in response_data:
            # Remove provider prefix if present (e.g., "OANDA:XAU_USD" -> "XAU/USD")
            raw_symbol = response_data["symbol"]
            if ":" in raw_symbol:
                raw_symbol = raw_symbol.split(":", 1)[1]
            symbol = raw_symbol.replace("_", "/")
        
        # Create standardized candle format
        candle = {
            "symbol": symbol,
            "timestamp": response_data["t"][idx],
            "open": float(response_data["o"][idx]),
            "high": float(response_data["h"][idx]),
            "low": float(response_data["l"][idx]),
            "close": float(response_data["c"][idx]),
            "volume": float(response_data["v"][idx]),
            "provider": "finnhub"
        }
        
        return candle
    except Exception as e:
        logger.error(f"Error parsing Finnhub response: {e}")
        return None 