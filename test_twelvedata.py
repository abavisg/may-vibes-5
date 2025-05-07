#!/usr/bin/env python3
"""
Test script for TwelveData API.
This script tests if the TwelveData API is working correctly with the provided API key.

Usage:
    python test_twelvedata.py [API_KEY] [SYMBOL]

If API_KEY is not provided, it will try to read it from the TWELVE_DATA_API_KEY environment variable.
If SYMBOL is not provided, it will default to "XAU/USD" (Gold).
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_twelvedata_api(api_key=None, symbol="XAU/USD"):
    """Test the TwelveData API with the provided API key."""
    
    # Try to get API key from argument or environment variable
    if not api_key:
        api_key = os.getenv("TWELVE_DATA_API_KEY")
    
    if not api_key:
        print("Error: No API key provided. Please provide an API key as argument or set the TWELVE_DATA_API_KEY environment variable.")
        return False
    
    print(f"Testing TwelveData API with key: {api_key[:5]}..." + "*" * (len(api_key) - 5))
    print(f"Using symbol: {symbol}")
    
    try:
        # Construct API URL
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&apikey={api_key}&format=JSON&dp=3"
        
        # Make the request
        print(f"Sending request to TwelveData API: {url}")
        response = requests.get(url)
        
        # Parse the response
        data = response.json()
        
        # Pretty print the response
        print("\nAPI Response:")
        print(json.dumps(data, indent=2))
        
        # Check if the response contains an error
        if data.get("status") == "error" or "code" in data:
            print(f"\nError from TwelveData API: {data.get('message', 'Unknown error')}")
            print("\nTry using a different symbol. Common symbols include:")
            print("  - AAPL (Apple Inc.)")
            print("  - MSFT (Microsoft)")
            print("  - EUR/USD (Euro/US Dollar)")
            print("  - BTC/USD (Bitcoin/US Dollar)")
            print("  - XAU/USD (Gold/US Dollar)")
            return False
        
        # Check if the response contains the expected data
        if "meta" not in data or "values" not in data:
            print("\nError: Unexpected response format from TwelveData API.")
            print("Make sure your API key has access to the requested symbol data.")
            return False
        
        # Check if values array is empty
        if not data["values"]:
            print("\nWarning: No candle data received. This could be due to market being closed or API limitations.")
            return False
        
        # Success
        print("\nSuccess! TwelveData API is working correctly.")
        print(f"Received data for {data['meta']['symbol']} at {data['meta']['interval']} interval.")
        
        # Extract the candle data
        candle = data["values"][0]
        print(f"\nLatest candle ({candle['datetime']}):")
        print(f"  Open:   {candle['open']}")
        print(f"  High:   {candle['high']}")
        print(f"  Low:    {candle['low']}")
        print(f"  Close:  {candle['close']}")
        print(f"  Volume: {candle.get('volume', 'N/A')}")
        
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP Error: {e}")
        
        if response.status_code == 401:
            print("Authentication error. Check if your API key is correct.")
        elif response.status_code == 429:
            print("Rate limit exceeded. You've made too many requests.")
        
        return False
    
    except requests.exceptions.RequestException as e:
        print(f"\nError connecting to TwelveData API: {e}")
        return False
    
    except json.JSONDecodeError:
        print("\nError parsing response from TwelveData API.")
        print("Response content:")
        print(response.text)
        return False
    
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

if __name__ == "__main__":
    # Get API key from command line argument if provided
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Get symbol from command line argument if provided
    symbol = sys.argv[2] if len(sys.argv) > 2 else "XAU/USD"
    
    # Test the API
    success = test_twelvedata_api(api_key, symbol)
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 