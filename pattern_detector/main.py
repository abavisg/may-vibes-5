import logging
import os
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our Ollama client
from pattern_detector.ollama_client import detect_patterns_with_ollama, detect_pattern_fallback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [pattern_detector] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Pattern detector service starting up")

# Feature flags
USE_SIGNAL_STUBS = os.getenv("USE_SIGNAL_STUBS", "false").lower() == "true"
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

logger.info(f"USE_SIGNAL_STUBS set to: {USE_SIGNAL_STUBS}")
logger.info(f"USE_OLLAMA set to: {USE_OLLAMA}")
if USE_OLLAMA:
    logger.info(f"Using Ollama model: {OLLAMA_MODEL}")

# Create FastAPI application
app = FastAPI(
    title="Pattern Detector",
    description="Service to detect patterns in candle data",
    version="0.1.0"
)

# Define request model
class Candle(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class PatternResponse(BaseModel):
    patterns: List[Dict[str, Any]]
    candle: Candle

# Middleware to log all incoming requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Received {request.method} request at {request.url.path}")
    response = await call_next(request)
    logger.info(f"Returning response with status code: {response.status_code}")
    return response

# Define API endpoints
@app.post("/detect")
async def detect_candle_pattern(candle: Candle) -> PatternResponse:
    """
    Analyze a candle for patterns and return the detection results.
    Uses Ollama if enabled, otherwise falls back to basic detection.
    """
    logger.info(f"Received candle data for pattern detection: {candle.symbol} at {candle.timestamp}")
    logger.debug(f"Full candle data: {candle.json()}")
    
    try:
        # Convert Pydantic model to dict
        candle_dict = candle.dict()
        
        # Check if we're using signal stubs
        if USE_SIGNAL_STUBS:
            logger.info("Using signal stubs, returning empty pattern list")
            # When using signal stubs, we don't need to detect patterns
            # Just return an empty pattern list
            return PatternResponse(
                patterns=[],
                candle=candle
            )
        
        # Detect pattern using Ollama or fallback
        patterns = []
        if USE_OLLAMA:
            logger.info(f"Using Ollama for pattern detection")
            try:
                patterns = await detect_patterns_with_ollama(candle_dict)
                logger.info(f"Ollama detected {len(patterns)} patterns")
            except Exception as e:
                logger.error(f"Error using Ollama for pattern detection: {str(e)}", exc_info=True)
                logger.info("Falling back to basic pattern detection")
                # If Ollama fails, fallback to the basic detector
                fallback_pattern = detect_pattern_fallback(candle_dict)
                patterns = [fallback_pattern] if fallback_pattern["strength"] > 0 else []
        else:
            logger.info(f"Using fallback pattern detection")
            fallback_pattern = detect_pattern_fallback(candle_dict)
            patterns = [fallback_pattern] if fallback_pattern["strength"] > 0 else []
        
        # Return in the format expected by the signal generator
        num_patterns = len(patterns)
        if num_patterns > 0:
            pattern_names = ", ".join([p.get("pattern", "unknown") for p in patterns])
            logger.info(f"Returning {num_patterns} detected patterns: {pattern_names}")
        else:
            logger.info(f"No patterns detected")
            
        return PatternResponse(
            patterns=patterns,
            candle=candle
        )
    except Exception as e:
        error_msg = f"Error analyzing candle: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    logger.info("Health check endpoint called")
    return {"status": "healthy", "service": "pattern_detector"}

@app.post("/explain")
async def explain_candle_pattern(candle: Candle):
    """
    Analyze a candle and provide a detailed explanation of any patterns found.
    Uses Ollama for pattern explanation if enabled.
    """
    logger.info(f"Received candle data for pattern explanation: {candle.symbol} at {candle.timestamp}")
    
    try:
        # Convert Pydantic model to dict
        candle_dict = candle.dict()
        
        # Check if Ollama is enabled
        if not USE_OLLAMA:
            return {
                "explanation": "Pattern explanation requires Ollama integration to be enabled (USE_OLLAMA=true)",
                "candle": candle
            }
        
        # Detect patterns using Ollama
        patterns = await detect_patterns_with_ollama(candle_dict)
        
        if not patterns:
            return {
                "explanation": "No significant patterns detected in this candle",
                "patterns": [],
                "candle": candle
            }
        
        # Create explanation text based on detected patterns
        pattern_names = ", ".join([p.get("pattern", "unknown") for p in patterns])
        
        # Collect explanation text for each pattern
        explanations = []
        for p in patterns:
            pattern_type = p.get("type", "neutral").upper()
            strength = p.get("strength", 0)
            description = p.get("description", "No description available")
            prediction = p.get("prediction", "No prediction available")
            
            explanation = f"{p.get('pattern', 'Unknown Pattern')} ({pattern_type}, Strength: {strength}/100): {description}. {prediction}"
            explanations.append(explanation)
        
        # Join explanations
        full_explanation = "\n\n".join(explanations)
        
        logger.info(f"Generated explanation for {pattern_names}")
        
        return {
            "explanation": full_explanation,
            "patterns": patterns,
            "candle": candle
        }
    except Exception as e:
        error_msg = f"Error explaining candle pattern: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(status_code=500, detail=error_msg)

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Pattern detector service is ready to receive requests") 