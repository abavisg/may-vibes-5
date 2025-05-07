# Signal Relay System

A multi-service architecture for processing financial market signals.

## 🧱 Tech Stack

- Python 3.11+
- FastAPI for microservices
- Uvicorn for development servers
- HTTPX for inter-service communication
- Ollama for AI-powered pattern detection

## 🧩 Components (Independent FastAPI Services)

- **Poller Service**: Fetches 1m XAUUSD candles periodically and sends to MCP
- **MCP Server**: Central orchestration service that routes candles to appropriate services
- **Pattern-Detector Host**: Analyzes candles and detects patterns using AI or rule-based algorithms
- **Signal Generator Host**: Generates trading signals based on patterns
- **Signal Dispatcher Host**: Dispatches signals to various outputs (logs, webhooks, etc.)

## 🤖 AI-Powered Pattern Detection

The Pattern Detector service now integrates with Ollama to provide advanced candlestick pattern recognition:

### Features

- **AI Pattern Recognition**: Uses Ollama LLMs to identify complex candlestick patterns like Engulfing, Doji, Hammers, etc.
- **Pattern Explanation**: Provides detailed explanations of detected patterns with price predictions
- **Configurable Models**: Works with any Ollama model (default: llama3:8b)
- **Graceful Fallback**: Falls back to rule-based detection when Ollama is unavailable
- **Two API Endpoints**: `/detect` for pattern detection and `/explain` for detailed explanations

### Configuration

Configure the Pattern Detector using these environment variables:

- `USE_OLLAMA`: Set to "true" to enable AI-powered pattern detection (default: true)
- `OLLAMA_MODEL`: The Ollama model to use (default: "llama3:8b")
- `OLLAMA_API_URL`: URL to the Ollama API (default: "http://localhost:11434/api/chat")
- `OLLAMA_TIMEOUT`: Timeout for Ollama API calls in seconds (default: 15)

### Example Output

AI-detected pattern:
```json
{
  "pattern": "Bullish Engulfing",
  "type": "bullish",
  "strength": 80,
  "description": "A strong bullish signal indicating a potential reversal from bearish trend",
  "prediction": "Possible short-term price increase"
}
```

### Requirements

- Ollama installed locally or remotely: [Install Ollama](https://ollama.ai/download)
- At least one LLM model available (e.g., run `ollama pull llama3:8b`)

## 🚀 How to Run

### Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:

   Create a `.env` file in the project root with the following settings:
   ```
   # TwelveData API key
   TWELVE_DATA_API_KEY=your_api_key_here

   # Poller stub mode (optional)
   USE_SIGNAL_STUBS=true
   
   # Ollama configuration
   USE_OLLAMA=true
   OLLAMA_MODEL=llama3:8b

   # Signal stub settings (only used by poller)
   BUY_SIGNAL_FREQUENCY=0.3
   SELL_SIGNAL_FREQUENCY=0.3
   ```

3. **TwelveData API Key (Optional but Recommended)**:
   
   The poller service can use real market data from TwelveData instead of mock data:
   
   - Sign up for a free account at [TwelveData](https://twelvedata.com/)
   - Get your API key from the dashboard
   - Add it to your `.env` file or set as an environment variable:
     ```
     export TWELVE_DATA_API_KEY=your_api_key_here
     ```
   - Without an API key, the system will fall back to generating mock candle data

4. **Ollama Setup (Optional but Recommended)**:
   
   For AI-powered pattern detection:
   
   - Install Ollama from [ollama.ai/download](https://ollama.ai/download)
   - Pull a language model: `ollama pull llama3:8b`
   - Set environment variables:
     ```
     export USE_OLLAMA=true
     export OLLAMA_MODEL=llama3:8b
     ```

5. **Run with Docker Compose (Recommended)**:
   ```
   docker-compose up
   ```
   
   To use your TwelveData API key with Docker Compose:
   ```
   TWELVE_DATA_API_KEY=your_api_key_here docker-compose up
   ```

6. **Run Locally**:
   
   You can use the helper script that starts all services in separate processes:
   ```
   ./run_local.py
   ```
   
   Or start each service manually in a separate terminal:

   ```bash
   # Start MCP Server (port 8000)
   cd mcp
   uvicorn main:app --reload --port 8000

   # Start Pattern Detector (port 8001)
   cd pattern_detector
   PYTHONPATH=.. uvicorn main:app --reload --port 8001

   # Start Signal Generator (port 8002)
   cd signal_generator
   uvicorn main:app --reload --port 8002

   # Start Signal Dispatcher (port 8003)
   cd signal_dispatcher
   uvicorn main:app --reload --port 8003

   # Start Poller Service (runs continuously)
   cd poller
   python main.py
   ```

## 🔁 Flow

1. Poller fetches candles from TwelveData (or generates mock data)
2. MCP receives candle at `/mcp/candle`
3. MCP routes to Pattern-Detector (using Ollama or rule-based detection)
4. If pattern is detected, calls Signal Generator
5. Signal Generator creates a signal
6. Signal is passed to Signal Dispatcher
7. Result: BUY/SELL signal for XAUUSD is logged or dispatched

## 📁 Project Structure

```
.
├── mcp/                      # Model Context Protocol service
│   ├── __init__.py
│   └── main.py
├── poller/                   # Candle data poller service
│   ├── __init__.py
│   ├── main.py               # FastAPI app with polling logic
│   ├── candle_generator.py   # Mock candle generation
│   ├── data_providers/       # Market data providers
│   │   ├── __init__.py
│   │   ├── twelvedata.py     # TwelveData API client
│   │   └── finnhub.py        # Finnhub API client
│   └── parsers/              # Response parsers for providers
│       ├── __init__.py
│       ├── twelvedata.py     # TwelveData response parser
│       └── finnhub.py        # Finnhub response parser
├── pattern_detector/         # Pattern detection service
│   ├── __init__.py
│   ├── main.py
│   └── ollama_client.py      # AI-powered pattern detection
├── signal_generator/         # Signal generation service
│   ├── __init__.py
│   ├── main.py
│   └── signal_stubs.py       # Stub implementations for signal generation
├── signal_dispatcher/        # Signal dispatching service
│   ├── __init__.py
│   └── main.py
├── signal_logs/              # Directory for signal log files
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── requirements.txt          # Python dependencies
├── run_local.py              # Helper script to run all services locally
├── test_twelvedata.py        # Script to test TwelveData API connectivity
└── README.md
```

## 📝 Configuration

The system can be configured using environment variables:

### Poller Service
- `MCP_URL`: URL of the MCP server (default: `http://localhost:8000/mcp/candle`)
- `POLLING_INTERVAL`: Time between candle polls in seconds (default: `30`)
- `TWELVE_DATA_API_KEY`: API key for TwelveData (optional, falls back to mock data if not provided)
- `USE_SIGNAL_STUBS`: If set, poller will generate mock candle data instead of fetching from TwelveData. **This only affects the poller.**
- `BUY_SIGNAL_FREQUENCY`, `SELL_SIGNAL_FREQUENCY`: Control the frequency of stub signals (only used if stubs are enabled in the poller).
- `DATA_PROVIDER`: Market data provider to use (default: `twelvedata`, other option: `finnhub`)

### MCP Server
- `PATTERN_DETECTOR_URL`: URL of the pattern detector service (default: `http://localhost:8001/detect`)
- `SIGNAL_GENERATOR_URL`: URL of the signal generator service (default: `http://localhost:8002/generate`)
- `SIGNAL_DISPATCHER_URL`: URL of the signal dispatcher service (default: `http://localhost:8003/dispatch`)

### Pattern Detector
- `USE_OLLAMA`: Enable AI-powered pattern detection (default: `true`)
- `OLLAMA_MODEL`: Model to use with Ollama (default: `llama3:8b`)
- `OLLAMA_API_URL`: URL to the Ollama API (default: `http://localhost:11434/api/chat`)
- `OLLAMA_TIMEOUT`: Timeout in seconds for Ollama requests (default: `15`)

### Signal Generator
- No stub or mock settings. Always generates signals based on input patterns.

### Signal Dispatcher
- `SIGNAL_LOG_DIR`: Directory for signal log files (default: `./signal_logs`)
- `WEBHOOK_URL`: URL to send signals to (optional, logs only if not provided)

## 📈 TwelveData API Integration

The Poller service can fetch real-time market data from the TwelveData API. Here's how the integration works:

1. If `TWELVE_DATA_API_KEY` is set, the Poller tries to fetch real candle data
2. If the API key is missing or the API call fails, it falls back to generating mock data
3. The API fetches 1-minute candles for XAU/USD (Gold/USD)
4. TwelveData offers a free tier that permits a limited number of API calls per minute/day
5. To modify the polling interval, adjust the `POLLING_INTERVAL` environment variable

With a free TwelveData account, you get:
- 800 API credits per day (~800 requests)
- 8 API credits per minute
- Access to OHLCV data for XAU/USD and many other symbols

To test your TwelveData API key:
```
python test_twelvedata.py
```

Or with a specific symbol:
```
python test_twelvedata.py YOUR_API_KEY XAU/USD
```

## 🔄 Development Features

The system includes several features to facilitate development:

### Poller Stubs (Mock Candle Data)

To develop and test signal handling without depending on real market data:

1. Set `USE_SIGNAL_STUBS=true` in your environment (only affects the poller)
2. Configure stub behavior with:
   - `BUY_SIGNAL_FREQUENCY`: Probability (0-1) of generating a BUY signal for each candle
   - `SELL_SIGNAL_FREQUENCY`: Probability (0-1) of generating a SELL signal for each candle

This allows testing the full pipeline with predictable signals without consuming TwelveData API quotas. All other services (pattern detector, MCP, signal generator, dispatcher) will process the data as normal, regardless of its source.

### Poller Service Code Improvements

The poller service has been refactored to improve code organization and reliability:

1. **Modular Design**: Created a reusable `fetch_and_process_candle()` helper function that centralizes candle processing logic
2. **Error Handling**: Added improved error handling with specific error messages for easier debugging
3. **Data Provider Configuration**: Service is configured to use TwelveData by default, but is designed to support multiple data providers
4. **API Endpoints**: Provides health check, last candle information, and manual polling trigger endpoints
5. **Background Processing**: Runs polling in a separate background task for better performance

### Pattern Detection Methods

The system supports three pattern detection methods:

1. **AI-Powered Detection**: Uses Ollama LLMs to identify complex patterns (`USE_OLLAMA=true`)
2. **Rule-Based Detection**: Uses simple algorithmic pattern detection (`USE_OLLAMA=false`)

### Development Modes

The system supports several operating modes:

1. **Full Production**: Uses TwelveData API for real market data with AI pattern detection
2. **Mixed Mode 1**: Uses mock market data with AI pattern detection (set `USE_SIGNAL_STUBS=true` in poller)
3. **Mixed Mode 2**: Uses real market data with rule-based pattern detection
4. **Development Mode**: Uses both mock data and poller stubs for end-to-end testing

Configure your mode by setting the appropriate environment variables in your `.env` file.

## 📊 TwelveData API Response Format

The API returns data in this format:
```json
{
    "meta": {
        "symbol": "XAU/USD",
        "interval": "1min",
        "currency": "USD",
        "exchange_timezone": "UTC",
        "exchange": "FOREX",
        "type": "Physical Currency"
    },
    "values": [
        {
            "datetime": "2023-05-10 12:23:00",
            "open": "2032.54004",
            "high": "2032.84998",
            "low": "2032.22998",
            "close": "2032.31995",
            "volume": "1234"
        }
    ],
    "status": "ok"
}
``` 