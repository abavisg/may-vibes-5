"""
CLI formatter for displaying trading signals in a clean format.
This is used by the signal dispatcher to show signals in the terminal.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def format_signal_for_cli(signal: Dict[str, Any]) -> str:
    """Format signal for CLI display in the requested format"""
    signal_type = signal["type"]
    
    if signal_type == "none" or signal.get("status") == "no_signal":
        return "NO SIGNAL GENERATED"
    
    entry_price = signal["entry_price"]
    stop_loss = signal["stop_loss"]
    take_profit = signal["take_profit"]
    
    # Simple format as requested
    message = f"""SIGNAL ALERT: 
{signal_type}
Price: {entry_price}
SL: {stop_loss}
TP: {take_profit}"""
    
    # Print directly to stdout for clean terminal display
    print(f"\n=== MESSAGING SIGNAL ===\n{message}\n======================")
    
    return message 