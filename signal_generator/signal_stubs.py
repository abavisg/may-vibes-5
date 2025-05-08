"""
Signal stubs for development and testing.
These stubs provide predictable signal generation without hitting external APIs.
"""

import datetime
import logging
import random
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BuySignalStub:
    """Stub implementation for generating BUY signals"""
    
    def __init__(self, frequency: float = 0.3):
        """
        Initialize the BUY signal stub.
        
        Args:
            frequency: Probability (0-1) of generating a signal for each candle
        """
        self.frequency = frequency
        self.counter = 0
    
    def analyze(self, candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze candle data and potentially generate a BUY signal.
        
        Args:
            candle: Candle data dict with OHLCV information
            
        Returns:
            Signal dict or None if no signal is generated
        """
        self.counter += 1
        
        # Generate a BUY signal with the configured frequency
        if random.random() < self.frequency:
            logger.info(f"BUY signal stub generating signal for candle {self.counter}")
            
            # Calculate some reasonable values for the signal
            entry_price = candle["close"]
            stop_loss = entry_price * 0.99  # 1% below entry
            take_profit = entry_price * 1.02  # 2% above entry
            
            return {
                "type_of_data": "DUMMY",
                "id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": "XAUUSD-Dummy", #candle["symbol"],
                "candle_timestamp": candle["timestamp"],
                "type": "BUY",
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "pattern": {
                    "type": "stub_pattern",
                    "confidence": random.uniform(0.6, 0.9),
                    "description": "Stub BUY pattern for testing"
                }
            }
        
        return None

class SellSignalStub:
    """Stub implementation for generating SELL signals"""
    
    def __init__(self, frequency: float = 0.3):
        """
        Initialize the SELL signal stub.
        
        Args:
            frequency: Probability (0-1) of generating a signal for each candle
        """
        self.frequency = frequency
        self.counter = 0
    
    def analyze(self, candle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze candle data and potentially generate a SELL signal.
        
        Args:
            candle: Candle data dict with OHLCV information
            
        Returns:
            Signal dict or None if no signal is generated
        """
        self.counter += 1
        
        # Generate a SELL signal with the configured frequency
        if random.random() < self.frequency:
            logger.info(f"SELL signal stub generating signal for candle {self.counter}")
            
            # Calculate some reasonable values for the signal
            entry_price = candle["close"]
            stop_loss = entry_price * 1.01  # 1% above entry
            take_profit = entry_price * 0.98  # 2% below entry
            
            return {
                "type_of_data": "DUMMY",
                "id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": candle["symbol"],
                "candle_timestamp": candle["timestamp"],
                "type": "SELL",
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "pattern": {
                    "type": "stub_pattern",
                    "confidence": random.uniform(0.6, 0.9),
                    "description": "Stub SELL pattern for testing"
                }
            }
        
        return None 