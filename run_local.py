#!/usr/bin/env python3
"""
Script to run all microservices locally in separate processes.
This is meant for development purposes only.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Define services and their ports
SERVICES = [
    {"name": "pattern_detector", "port": 8001, "module": "pattern_detector.main:app"},
    {"name": "signal_generator", "port": 8002, "module": "signal_generator.main:app"},
    {"name": "signal_dispatcher", "port": 8003, "module": "signal_dispatcher.main:app"},
    {"name": "mcp", "port": 8000, "module": "mcp.main:app"},  # Model Context Protocol
]

# Poller is started last (after all APIs are up)
POLLER = {"name": "poller", "module": "poller.main"}

# List to keep track of running processes
processes = []

def create_directories():
    """Create necessary directories"""
    # Create signal_logs directory
    Path("signal_logs").mkdir(exist_ok=True)
    
    # Create __init__.py files for each service to make them importable
    for service in SERVICES:
        init_file = Path(service["name"]) / "__init__.py"
        init_file.parent.mkdir(exist_ok=True)
        init_file.touch(exist_ok=True)
    
    Path("poller").mkdir(exist_ok=True)
    (Path("poller") / "__init__.py").touch(exist_ok=True)

def cleanup(sig=None, frame=None):
    """Clean up function to kill all processes on exit"""
    print("\nShutting down all services...")
    
    for process in processes:
        try:
            process.terminate()
            time.sleep(0.5)  # Give it time to terminate gracefully
            if process.poll() is None:  # If still running
                process.kill()  # Force kill
        except:
            pass
    
    print("All services stopped.")
    sys.exit(0)

def get_poller_env():
    """Get environment variables for the poller service"""
    env = os.environ.copy()
    
    # Set default environment variables if they don't exist
    if "MCP_URL" not in env:
        env["MCP_URL"] = "http://localhost:8000/mcp/candle"
    
    if "POLLING_INTERVAL" not in env:
        env["POLLING_INTERVAL"] = "30"
    
    # Note: TWELVE_DATA_API_KEY will be passed as-is if it exists in the environment
    
    return env

def main():
    """Main function to start all services"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Create necessary directories
    create_directories()
    
    try:
        # Start FastAPI services
        for service in SERVICES:
            name = service["name"]
            port = service["port"]
            module = service["module"]
            
            print(f"Starting {name} service on port {port}...")
            cmd = ["uvicorn", module, "--reload", "--port", str(port)]
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                # Redirect stdout and stderr to the parent process
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line-buffered
            )
            
            processes.append(process)
            print(f"{name} service started with PID {process.pid}")
        
        # Wait a bit for services to start
        print("Waiting for API services to start...")
        time.sleep(3)
        
        # Start the poller service
        print(f"Starting {POLLER['name']} service...")
        
        # Get environment variables for the poller
        poller_env = get_poller_env()
        
        # Check if TwelveData API key is set
        if "TWELVE_DATA_API_KEY" in poller_env:
            print(f"TwelveData API key is set, will use real market data")
        else:
            print(f"TwelveData API key is not set, will use mock candle data")
        
        poller_process = subprocess.Popen(
            [sys.executable, "-m", POLLER["module"]],
            # Redirect stdout and stderr to the parent process
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line-buffered
            env=poller_env,  # Pass environment variables
        )
        
        processes.append(poller_process)
        print(f"{POLLER['name']} service started with PID {poller_process.pid}")
        
        # Process output from all processes
        while True:
            for process in processes:
                if process.poll() is not None:
                    # Process has terminated
                    print(f"Process with PID {process.pid} has exited with code {process.returncode}")
                    cleanup()
                
                # Read output
                line = process.stdout.readline()
                if line:
                    print(f"[PID {process.pid}] {line.strip()}")
            
            time.sleep(0.1)
        
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()

if __name__ == "__main__":
    main() 