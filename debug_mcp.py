#!/usr/bin/env python3
"""
Debug script to run the MCP service with enhanced error logging
"""

import sys
import subprocess
import time
import os

def main():
    # Set environment variables for better debugging
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output
    env["LOGLEVEL"] = "DEBUG"      # Increase log level if respected by FastAPI/uvicorn
    
    # Run MCP with detailed logging
    print("Starting MCP with debug logging...")
    
    # Start the MCP service in a way that captures all output
    cmd = [
        sys.executable, "-m", "uvicorn", "mcp.main:app", 
        "--reload", "--port", "8000",
        "--log-level", "debug"
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    print(f"MCP started with PID {process.pid}. Monitoring logs:")
    print("=" * 80)
    
    # Wait for the MCP service to start and show its logs
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                # Process has terminated
                print(f"MCP process terminated with code {process.returncode}")
                break
                
            if line:
                print(line.strip())
                
            # Check for process termination
            if process.poll() is not None:
                print(f"MCP process terminated with code {process.returncode}")
                break
                
    except KeyboardInterrupt:
        print("Stopping debug session...")
    finally:
        if process.poll() is None:  # If process is still running
            print("Terminating MCP process...")
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                print("MCP didn't terminate gracefully, killing...")
                process.kill()
    
    print("Debug session ended.")

if __name__ == "__main__":
    main() 