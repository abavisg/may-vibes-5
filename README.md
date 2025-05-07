# Signal Relay System

A multi-service architecture for processing financial market signals.

## 🧱 Tech Stack

- Python 3.11+
- FastAPI for microservices
- Uvicorn for development servers
- HTTPX for inter-service communication

## 🧩 Components (Independent FastAPI Services)

- **Poller Service**: Fetches 1m XAUUSD candles periodically and sends to MCP
- **MCP Server**: Central orchestration service that routes candles to appropriate services
- **Pattern-Detector Host**: Analyzes candles and detects patterns
- **Signal Generator Host**: Generates trading signals based on patterns
- **Signal Dispatcher Host**: Dispatches signals to various outputs (logs, webhooks, etc.)

## 🚀 How to Run

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Start each service in a separate terminal:

   ```bash
   # Start MCP Server (port 8000)
   cd mcp
   uvicorn main:app --reload --port 8000

   # Start Pattern Detector (port 8001)
   cd pattern_detector
   uvicorn main:app --reload --port 8001

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

1. Poller fetches candles from provider (e.g., Twelve Data)
2. MCP receives candle at `/mcp/candle`
3. MCP routes to Pattern-Detector
4. If pattern is detected, calls Signal Generator
5. Signal Generator creates a signal
6. Signal is passed to Signal Dispatcher
7. Result: BUY/SELL signal for XAUUSD is logged or dispatched

## 📁 Project Structure

```
.
├── mcp/
│   └── main.py
├── poller/
│   └── main.py
├── pattern_detector/
│   └── main.py
├── signal_generator/
│   └── main.py
├── signal_dispatcher/
│   └── main.py
├── requirements.txt
└── README.md
``` 