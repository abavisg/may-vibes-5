"""
Parser for TwelveData API responses.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def parse_candle_response(response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse TwelveData response into a standardized candle format."""
    try:
        # Check if response has expected structure
        if not response_data or "meta" not in response_data or "values" not in response_data:
            logger.warning("Invalid TwelveData response format")
            return None
        
        meta = response_data["meta"]
        values = response_data["values"]
        
        if not values or len(values) == 0:
            logger.warning("No values in TwelveData response")
            return None
        
        # Get the latest candle (first in the list)
        latest = values[0]
        
        # Format timestamp
        datetime_str = latest.get("datetime", "")
        timestamp = int(datetime.fromisoformat(datetime_str).timestamp()) if datetime_str else int(datetime.now().timestamp())
        
        # Create standardized candle format
        candle = {
            "symbol": meta.get("symbol", "UNKNOWN"),
            "timestamp": timestamp,
            "open": float(latest.get("open", 0)),
            "high": float(latest.get("high", 0)),
            "low": float(latest.get("low", 0)),
            "close": float(latest.get("close", 0)),
            "volume": float(latest.get("volume", 0)),
            "provider": "twelvedata"
        }
        
        return candle
    except Exception as e:
        logger.error(f"Error parsing TwelveData response: {e}")
        return None 