#!/usr/bin/env python3
"""
Simple script to test health checks for a service
"""

import sys
import time
import requests

def check_health(port):
    """Check health of service at the given port"""
    url = f"http://localhost:{port}/health"
    print(f"Checking health at {url}")
    
    try:
        response = requests.get(url, timeout=2.0)
        print(f"Status code: {response.status_code}")
        print(f"Response content: {response.text}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON data: {data}")
                print(f"Status from response: {data.get('status')}")
                return True
            except Exception as e:
                print(f"Error parsing JSON: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {e}")
        return False

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    print(f"Testing health check for port {port}")
    result = check_health(port)
    print(f"Health check result: {result}") 