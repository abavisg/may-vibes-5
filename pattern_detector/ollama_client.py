"""
Ollama client for pattern detection.
This module uses Ollama to detect candlestick patterns in price data.
"""

import json
import logging
import os
import httpx
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "15"))  # seconds

async def detect_patterns_with_ollama(candle: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect candlestick patterns using Ollama LLM API.
    
    Args:
        candle: Dict containing OHLCV data
        
    Returns:
        List of detected patterns with details
    """
    logger.info(f"Analyzing candle with Ollama for {candle['symbol']} at {candle['timestamp']}")
    
    # Extract price data
    symbol = candle["symbol"]
    timestamp = candle["timestamp"]
    open_price = candle["open"]
    high_price = candle["high"]
    low_price = candle["low"]
    close_price = candle["close"]
    volume = candle["volume"]
    
    # Calculate additional metrics that might be useful for pattern detection
    body_size = abs(close_price - open_price)
    price_range = high_price - low_price
    is_bullish = close_price > open_price
    body_percent = (body_size / price_range) * 100 if price_range > 0 else 0
    
    # Prepare the prompt for Ollama
    prompt = f"""
You are an expert technical analyst specializing in candlestick patterns. 
Analyze the following candlestick data for {symbol} and identify any recognizable patterns.

Candlestick data for {timestamp}:
- Open: {open_price}
- High: {high_price}
- Low: {low_price}
- Close: {close_price}
- Volume: {volume}

Additional metrics:
- Body size: {body_size:.2f}
- Price range: {price_range:.2f}
- Direction: {"Bullish" if is_bullish else "Bearish"}
- Body percentage of range: {body_percent:.2f}%

Identify any candlestick patterns present in this single candle.
If multiple patterns are present, list them all.
For each pattern, provide:
1. Pattern name
2. Pattern type (bullish, bearish, or neutral)
3. Pattern strength (0-100 scale)
4. Brief description of what this pattern suggests for future price movement

Respond in the following JSON format only:
{{
  "patterns": [
    {{
      "pattern": "pattern_name",
      "type": "bullish|bearish|neutral",
      "strength": 75,
      "description": "Brief description of what this pattern indicates",
      "prediction": "Possible short-term price movement"
    }}
  ]
}}

If no recognizable patterns are found, return an empty patterns array.
"""
    
    try:
        # Call Ollama API
        logger.info(f"Sending request to Ollama API for {symbol}")
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
                OLLAMA_API_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert financial analyst specializing in candlestick patterns. Respond only with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for more deterministic results
                        "top_p": 0.9
                    }
                }
            )
            
            # Check for successful response
            response.raise_for_status()
            result = response.json()
            
            # Extract the response text
            response_text = result.get("message", {}).get("content", "")
            logger.debug(f"Ollama raw response: {response_text}")
            
            # Extract JSON from the response (handling possible text before/after the JSON)
            try:
                # Try to find JSON blocks in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    data = json.loads(json_str)
                    patterns = data.get("patterns", [])
                    
                    # Enhance patterns with candle timestamp
                    for pattern in patterns:
                        pattern["candle_timestamp"] = timestamp
                        
                        # Add details section expected by the signal generator
                        pattern["details"] = {
                            "body_size": body_size,
                            "upper_shadow": high_price - (close_price if is_bullish else open_price),
                            "lower_shadow": (open_price if is_bullish else close_price) - low_price
                        }
                    
                    logger.info(f"Successfully extracted {len(patterns)} patterns from Ollama response")
                    return patterns
                else:
                    logger.warning(f"No valid JSON found in Ollama response")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Ollama response: {e}")
                return []
    except httpx.RequestError as e:
        logger.error(f"Error calling Ollama API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in Ollama pattern detection: {e}", exc_info=True)
        return []
        
# Fallback pattern detection for when Ollama is not available
def detect_pattern_fallback(candle: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple pattern detection logic as fallback when Ollama is not available.
    """
    logger.info(f"Using fallback pattern detection for {candle['symbol']} at {candle['timestamp']}")
    
    # Extract required data
    open_price = candle["open"]
    close_price = candle["close"]
    high_price = candle["high"]
    low_price = candle["low"]
    
    # Calculate candle body size (absolute value)
    body_size = abs(close_price - open_price)
    
    # Calculate upper and lower shadows
    if close_price >= open_price:  # Bullish candle
        upper_shadow = high_price - close_price
        lower_shadow = open_price - low_price
        logger.debug(f"Bullish candle detected: body={body_size}, upper_shadow={upper_shadow}, lower_shadow={lower_shadow}")
    else:  # Bearish candle
        upper_shadow = high_price - open_price
        lower_shadow = close_price - low_price
        logger.debug(f"Bearish candle detected: body={body_size}, upper_shadow={upper_shadow}, lower_shadow={lower_shadow}")
    
    # Price difference threshold (simple version - in a real system this would be more sophisticated)
    threshold = 0.001 * open_price  # 0.1% of open price
    logger.debug(f"Using price threshold of {threshold}")
    
    # Simple pattern detection logic
    pattern_name = "neutral"
    pattern_type = "neutral"
    pattern_strength = 0
    pattern_description = "No significant pattern detected"
    
    # Bullish pattern: Close significantly higher than open
    if close_price > open_price and (close_price - open_price) > threshold:
        pattern_name = "bullish_candle"
        pattern_type = "bullish"
        pattern_strength = min(100, int((close_price - open_price) / threshold * 10))
        pattern_description = "Bullish candle indicating potential upward momentum"
        logger.info(f"Bullish pattern detected with strength {pattern_strength}")
    
    # Bearish pattern: Close significantly lower than open
    elif open_price > close_price and (open_price - close_price) > threshold:
        pattern_name = "bearish_candle"
        pattern_type = "bearish"
        pattern_strength = min(100, int((open_price - close_price) / threshold * 10))
        pattern_description = "Bearish candle indicating potential downward momentum"
        logger.info(f"Bearish pattern detected with strength {pattern_strength}")
    else:
        logger.info(f"Neutral pattern detected")
    
    # Return the detected pattern
    pattern_result = {
        "pattern": pattern_name,
        "type": pattern_type,
        "strength": pattern_strength,
        "description": pattern_description,
        "prediction": "Sideways movement likely" if pattern_type == "neutral" else f"Potential {pattern_type} movement in the short term",
        "details": {
            "body_size": body_size,
            "upper_shadow": upper_shadow,
            "lower_shadow": lower_shadow
        },
        "candle_timestamp": candle["timestamp"]
    }
    
    logger.info(f"Fallback pattern detection completed: {pattern_name} with strength {pattern_strength}")
    return pattern_result 