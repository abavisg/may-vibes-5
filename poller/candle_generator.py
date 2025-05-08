"""
External candle generator for development and testing.
This module generates realistic OHLCV candle data without using external APIs.
"""

import datetime
import random
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class DummyCandleGenerator:
    """External candle generator implementation"""
    
    def __init__(self, symbol="XAUUSD", base_price=8000.0, volatility=0.001):
        """
        Initialize the candle generator.
        
        Args:
            symbol: The trading symbol (default: XAUUSD)
            base_price: Starting price in USD
            volatility: Price volatility factor (0.001 = 0.1%)
        """
        self.symbol = symbol
        self.last_price = base_price
        self.volatility = volatility
        logger.info(f"Initialized dummy candle generator for {symbol} with base price {base_price}")
    
    def generate_candle(self) -> Dict:
        """
        Generate a realistic OHLCV candle.
        
        Returns:
            Dict containing candle data with symbol, timestamp, OHLCV values
        """
        # Calculate price movement (random walk with slight upward bias)
        price_change = self.last_price * self.volatility * (2 * random.random() - 0.98)
        
        # Generate OHLC data
        open_price = self.last_price
        close_price = open_price + price_change
        
        # High is the maximum of open and close, plus some random amount
        high_price = max(open_price, close_price) + abs(price_change) * 0.5 * random.random()
        
        # Low is the minimum of open and close, minus some random amount
        low_price = min(open_price, close_price) - abs(price_change) * 0.5 * random.random()
        
        # Update last price for next candle
        self.last_price = close_price
        
        # Create candle with current timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate a random volume between 100 and 1000
        volume = random.randint(100, 1000)
        
        # Create and return the candle data
        return {
            "type_of_data": "DUMMY",
            "symbol": self.symbol,
            "timestamp": timestamp,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        }

# Create a singleton instance
_generator = DummyCandleGenerator()

def generate_dummy_candles() -> Dict:
    """
    Generate a candle using the singleton generator instance.
    This is the main function to be imported and used by other modules.
    
    Returns:
        Dict containing candle data
    """
    return _generator.generate_candle()

# For testing purposes
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
    )
    
    # Test the generator
    generator = DummyCandleGenerator()
    for _ in range(5):
        candle = generator.generate_candle()
        print(f"Generated candle: {candle}") 