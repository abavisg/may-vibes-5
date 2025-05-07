# How to Run the Market Signal Processing System

This document provides detailed instructions on how to run the Market Signal Processing System.

## Prerequisites

- Python 3.10+ installed
- pip package manager
- Git (for cloning the repository)

## Install Dependencies

First, install all the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The system uses environment variables for configuration. Create a `.env` file in the project root with the following settings:

```
# TwelveData API key (optional)
TWELVE_DATA_API_KEY=your_api_key_here

# Feature toggles
FORCE_MOCK_DATA=true
USE_SIGNAL_STUBS=true

# Signal stub settings
BUY_SIGNAL_FREQUENCY=0.5
SELL_SIGNAL_FREQUENCY=0.3
```

### Configuration Options

- `TWELVE_DATA_API_KEY`: Your TwelveData API key for real market data
- `FORCE_MOCK_DATA`: Set to "true" to use mock data even if an API key is provided
- `USE_SIGNAL_STUBS`: Set to "true" to use stub signal generators
- `BUY_SIGNAL_FREQUENCY`: Probability (0-1) of generating BUY signals
- `SELL_SIGNAL_FREQUENCY`: Probability (0-1) of generating SELL signals

## Running Methods

There are two ways to run the system:

### Method 1: Using the run_local.py Script (Recommended)

The easiest way to run all services is to use the provided run_local.py script:

```bash
python run_local.py
```

This script will:
1. Start all services in the correct order
2. Set up proper environment variables
3. Handle process output and error logging
4. Clean up processes when you press Ctrl+C

### Method 2: Running Services Manually

If you need more control, you can run each service manually in separate terminal windows.

#### Step 1: Start the MCP Server (Main Control Program)

```bash
python -m uvicorn mcp.main:app --reload --port 8000
```

#### Step 2: Start the Pattern Detector

```bash
python -m uvicorn pattern_detector.main:app --reload --port 8001
```

#### Step 3: Start the Signal Generator

```bash
python -m uvicorn signal_generator.main:app --reload --port 8002
```

#### Step 4: Start the Signal Dispatcher

```bash
python -m uvicorn signal_dispatcher.main:app --reload --port 8003
```

#### Step 5: Start the Poller Service

```bash
python -m poller.main
```

## Verifying the System

To verify that the system is running correctly:

1. Check that all services are running:
   ```bash
   ps aux | grep "uvicorn\|poller" | grep -v grep
   ```

2. Check the health of each service:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   ```

3. Check for signal log files:
   ```bash
   ls -la signal_logs/
   ```

4. Send a test candle to the MCP:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"symbol":"XAUUSD", "timestamp":"2025-05-07 12:00:00", "open": 2000.0, "high": 2010.0, "low": 1990.0, "close": 2005.0, "volume": 1000}' http://localhost:8000/mcp/candle
   ```

## Troubleshooting

If you encounter issues:

1. **Services not starting**: Check if the ports are already in use
   ```bash
   netstat -an | grep 800
   ```

2. **No signals being generated**: Make sure `USE_SIGNAL_STUBS=true` and signal frequencies are set high enough in `.env`

3. **Poller not connecting to MCP**: Check that MCP is running and accessible

4. **TwelveData API not working**: Test the API key with the test script
   ```bash
   python test_twelvedata.py
   ```

5. **Import errors**: If you see "ModuleNotFoundError" errors, make sure all __init__.py files are in place:
   ```bash
   # Create __init__.py files if missing
   touch mcp/__init__.py pattern_detector/__init__.py signal_generator/__init__.py signal_dispatcher/__init__.py poller/__init__.py
   ```

6. **Permission issues with run_local.py**: If the script can't be executed, set proper permissions:
   ```bash
   chmod +x run_local.py
   ```

7. **Python version issues**: Make sure you're using Python 3.10+ and have all dependencies installed:
   ```bash
   python --version
   pip install -r requirements.txt
   ```

8. **Killing all processes**: If you need to stop all services
   ```bash
   ps aux | grep "uvicorn\|poller" | grep -v grep | awk '{print $2}' | xargs kill -9
   ```

9. **Clean up cached files**: If you're experiencing strange behavior, try removing Python cache files:
   ```bash
   find . -name "__pycache__" -type d | xargs rm -rf
   ```

## Development Modes

The system supports three operating modes:

1. **Full Production**: Uses TwelveData API for real market data with actual pattern detection
2. **Mixed Mode**: Uses external candle generator with real pattern detection
3. **Development Mode**: Uses external candle generator and signal stubs

Configure your mode by setting the appropriate environment variables in your `.env` file. 