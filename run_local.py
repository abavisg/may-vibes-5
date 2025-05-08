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
import requests
from pathlib import Path

# Define the logs directory
LOG_DIR = "logs"

# Ensure the logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# --- Clear existing log files ---
print("Clearing existing log files in the logs directory...")
try:
    for filename in os.listdir(LOG_DIR):
        if filename.endswith(".log"):
            file_path = os.path.join(LOG_DIR, filename)
            try:
                with open(file_path, 'w') as f:
                    f.truncate(0) # Empty the file
                print(f"Cleared log file: {filename}")
            except Exception as e:
                print(f"Error clearing log file {filename}: {e}")
except Exception as e:
    print(f"Error accessing logs directory: {e}")
print("Log file clearing complete.")
# -----------------------------------

# Define services and their ports
SERVICES = [
    {"name": "pattern_detector", "port": 8001, "module": "pattern_detector.main:app"},
    {"name": "signal_generator", "port": 8002, "module": "signal_generator.main:app"},
    {"name": "signal_dispatcher", "port": 8003, "module": "signal_dispatcher.main:app"},
    {"name": "mcp", "port": 8000, "module": "mcp.main:app"},  # Model Context Protocol
    {"name": "poller", "port": 8004, "module": "poller.main:app"},  # Poller runs on port 8004
]

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

def cleanup_current_run(sig=None, frame=None):
    """Clean up function to kill all processes started by this run"""
    print("\nShutting down all services started by this run...")
    
    for process in processes:
        try:
            if process.poll() is None:  # Check if process is still running
                process.terminate()
                try:
                    # Wait for a short period for graceful termination
                    process.wait(timeout=1.0) 
                except subprocess.TimeoutExpired:
                    if process.poll() is None: # If still running after timeout
                        print(f"Process {process.pid} did not terminate gracefully, killing.")
                        process.kill() # Force kill
            # else:
            #     print(f"Process {process.pid} already terminated.")
        except Exception as e:
            print(f"Error terminating process {process.pid if process else 'unknown'}: {e}")
    
    processes.clear() # Clear the list of processes for this run
    print("All services from this run stopped.")
    if sig is not None: # If called as a signal handler, exit
        sys.exit(0)

def stop_existing_services():
    """Attempt to stop any relevant existing service processes."""
    print("Attempting to stop any existing service instances...")
    
    # Stop uvicorn services (FastAPI)
    # Using -f to match the full command line, targeting uvicorn processes for these specific modules
    # This is a bit more targeted than a blanket `pkill -f uvicorn`
    service_modules = [s["module"].split(':')[0] for s in SERVICES if s.get("is_api", True)] # e.g., "pattern_detector.main"
    for sm_part in service_modules:
        # This will match commands like "uvicorn pattern_detector.main:app ..."
        subprocess.run(["pkill", "-f", f"uvicorn.*{sm_part}"], check=False)

    # Stop poller service (can be run as module or script)
    poller_service = next((s for s in SERVICES if s["name"] == "poller"), None)
    if poller_service:
        subprocess.run(["pkill", "-f", poller_service["module"]], check=False) # e.g., poller.main
        subprocess.run(["pkill", "-f", f"{poller_service['name']}/{poller_service['module'].split('.')[-1]}.py"], check=False) # e.g., poller/main.py
    
    # Additional step: Kill any process using the ports we need
    for service in SERVICES:
        if "port" in service:
            port = service["port"]
            # Try to identify and kill any process using this port (macOS/Linux)
            try:
                # Get PID of process using the port
                lsof_cmd = f"lsof -i :{port} -t"
                result = subprocess.run(lsof_cmd, shell=True, capture_output=True, text=True, check=False)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    print(f"Found processes using port {port}: {pids}")
                    for pid in pids:
                        if pid.strip():
                            print(f"Killing process {pid} that is using port {port}")
                            subprocess.run(["kill", "-9", pid.strip()], check=False)
            except Exception as e:
                print(f"Error trying to kill process on port {port}: {e}")

    print("Waiting a few seconds for services to terminate...")
    time.sleep(3) # Allow time for processes to shut down
    print("Attempt to stop existing services complete.")

def wait_for_service_health(name, port, max_attempts=30, delay=1.0):
    """
    Check if a service is healthy by polling its /health endpoint.
    Returns True if healthy, False if not available after max_attempts.
    """
    health_url = f"http://localhost:{port}/health"
    print(f"Waiting for {name} to be healthy at {health_url}...")
    
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            print(f"Health check attempt {attempt}/{max_attempts} for {name}...")
            response = requests.get(health_url, timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    print(f"{name} is healthy after {attempt} attempts.")
                    return True
                else:
                    print(f"{name} responded with status: {data.get('status', 'unknown')}")
            else:
                print(f"Got status code {response.status_code} from {name}")
        except Exception as e:
            if attempt % 5 == 0:  # Log every 5 attempts
                print(f"Still waiting for {name} to be healthy... ({e})")
        
        # Sleep between attempts
        time.sleep(delay)
    
    print(f"ERROR: {name} did not become healthy after {max_attempts} attempts.")
    return False

def get_poller_env():
    """Get environment variables for the poller service.
    This version simply passes through the current environment.
    Services are expected to manage their own defaults or use .env files.
    """
    return os.environ.copy()

def main():
    """Main function to start all services"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup_current_run)
    signal.signal(signal.SIGTERM, cleanup_current_run)
    
    try:
        # First, stop any existing services
        stop_existing_services()
        
        # Create necessary directories
        create_directories()
        
        # Start the API services first
        api_services = [s for s in SERVICES if s.get("is_api", True)]
        non_api_services = [s for s in SERVICES if not s.get("is_api", True)]
        
        # Start each API service in sequence
        for service in api_services:
            name = service["name"]
            port = service["port"]
            module = service["module"]
            
            print(f"Starting {name} service on port {port}...")
            
            # Start the process with reduced Uvicorn log level
            cmd = [sys.executable, "-m", "uvicorn", module, "--reload", "--port", str(port), "--log-level", "warning"]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            
            processes.append(process)
            print(f"{name} service started with PID {process.pid}")
            
            # Wait for service to be healthy before proceeding
            if not wait_for_service_health(name, port):
                print(f"ERROR: {name} service failed to become healthy. Stopping all services.")
                cleanup_current_run()
                return
            
            print(f"{name} service is ready and healthy. Starting next service...")
        
        # All API services are now running, start the non-API services (like poller)
        for service in non_api_services:
            name = service["name"]
            module = service["module"]
            print(f"Starting {name} service...")
            # Configure environment if needed
            service_env = os.environ.copy()
            if name == "poller":
                service_env = get_poller_env()
                # Give more info about poller config
                if "TWELVE_DATA_API_KEY" in service_env:
                    print(f"Poller will attempt to use TwelveData API key.")
                else:
                    print(f"Poller will use mock candle data (API key not set).")
            # Start the service
            cmd = [sys.executable, "-m", module]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=service_env,
            )
            processes.append(process)
            print(f"{name} service started with PID {process.pid}")
        
        # Monitor logs from all services
        print("\nAll services started successfully. Monitoring logs:")
        print("=" * 80)
        
        while True:
            all_exited = True
            for i, proc in enumerate(processes):
                if proc.poll() is None:  # Process is still running
                    all_exited = False
                    try:
                        line = proc.stdout.readline()
                        if line:
                            # Service name may be different than the index if processes are started in a different order
                            service_name = f"service-{i}"  # Default fallback
                            if i < len(SERVICES):
                                service_name = SERVICES[i]["name"]
                            print(f"[PID {proc.pid} | {service_name}] {line.strip()}", flush=True)
                    except Exception:
                        pass
                elif proc in processes:  # Process has terminated
                    service_name = f"service-{i}"  # Default fallback
                    if i < len(SERVICES):
                        service_name = SERVICES[i]["name"]
                    print(f"Process {service_name} (PID {proc.pid}) has exited with code {proc.returncode}")
                    print("A service has terminated unexpectedly. Shutting down all services.")
                    cleanup_current_run()
                    return
            
            if all_exited:
                print("All processes have terminated.")
                break
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received.")
    except Exception as e:
        print(f"Error in main: {e}")
    finally:
        cleanup_current_run()

if __name__ == "__main__":
    main() 