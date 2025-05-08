import logging
import os
import sys # Import sys for StreamHandler
from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import time # Import time for measuring duration

# Import our Ollama client
from pattern_detector.ollama_client import detect_patterns_with_ollama, detect_pattern_fallback

# Load environment variables
load_dotenv()

# Import the ServiceLogger
from utils.logging_utils import ServiceLogger

# Initialize the logger for the pattern detector service
logger = ServiceLogger("pattern_detector").get_logger()

# Feature flags
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")

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
    response = await call_next(request)
    return response

@app.post("/detect")
async def detect_candle_pattern(candle: Candle) -> PatternResponse:
    logger.info(f"[START] /detect for {candle.symbol} at {candle.timestamp}")
    logger.info(f"Input: {candle.dict()}")
    try:
        candle_dict = candle.dict()
        patterns = []
        if USE_OLLAMA:
            logger.info(f"Using Ollama for pattern detection for {candle.symbol}")
            try:
                patterns = await detect_patterns_with_ollama(candle_dict)
                if not patterns:
                    logger.info(f"Ollama detected no patterns for {candle.symbol}")
            except Exception as e:
                logger.error(f"Ollama pattern detection failed for {candle.symbol}: {e}. Falling back.")
                fallback_pattern = detect_pattern_fallback(candle_dict)
                patterns = [fallback_pattern] if fallback_pattern["strength"] > 0 else []
                if patterns:
                    logger.info(f"Fallback detected a pattern for {candle.symbol}")
                else:
                    logger.info(f"Fallback detected no patterns for {candle.symbol}")
        else:
            logger.info(f"Ollama is disabled. Using fallback pattern detection for {candle.symbol}")
            fallback_pattern = detect_pattern_fallback(candle_dict)
            patterns = [fallback_pattern] if fallback_pattern["strength"] > 0 else []
            if patterns:
                logger.info(f"Fallback detected a pattern for {candle.symbol}")
            else:
                logger.info(f"Fallback detected no patterns for {candle.symbol}")

        result = PatternResponse(patterns=patterns, candle=candle)
        logger.info(f"Output: {result.dict()}")
        logger.info(f"[END] /detect for {candle.symbol} at {candle.timestamp}")
        return result
    except Exception as e:
        logger.error(f"Error analyzing candle: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing candle: {str(e)}")

@app.get("/health")
async def health_check():
    logger.info("[HEALTH] pattern_detector healthy check")
    return {"status": "healthy", "service": "pattern_detector"}

@app.post("/explain")
async def explain_candle_pattern(candle: Candle):
    logger.info(f"[START] /explain for {candle.symbol} at {candle.timestamp}")
    logger.info(f"Input: {candle.dict()}")
    try:
        candle_dict = candle.dict()
        if not USE_OLLAMA:
            result = {
                "explanation": "Pattern explanation requires Ollama integration to be enabled (USE_OLLAMA=true)",
                "candle": candle
            }
            logger.info(f"Output: {result}")
            logger.info(f"[END] /explain for {candle.symbol} at {candle.timestamp}")
            return result
        patterns = await detect_patterns_with_ollama(candle_dict)
        if not patterns:
            result = {
                "explanation": "No significant patterns detected in this candle",
                "patterns": [],
                "candle": candle
            }
            logger.info(f"Output: {result}")
            logger.info(f"[END] /explain for {candle.symbol} at {candle.timestamp}")
            return result
        pattern_names = ", ".join([p.get("pattern", "unknown") for p in patterns])
        explanations = []
        for p in patterns:
            pattern_type = p.get("type", "neutral").upper()
            strength = p.get("strength", 0)
            description = p.get("description", "No description available")
            prediction = p.get("prediction", "No prediction available")
            explanation = f"{p.get('pattern', 'Unknown Pattern')} ({pattern_type}, Strength: {strength}/100): {description}. {prediction}"
            explanations.append(explanation)
        full_explanation = f"Detected pattern(s): {pattern_names}\n\n" + "\n\n".join(explanations)
        result = {
            "explanation": full_explanation,
            "patterns": patterns,
            "candle": candle
        }
        logger.info(f"Output: {result}")
        logger.info(f"[END] /explain for {candle.symbol} at {candle.timestamp}")
        return result
    except Exception as e:
        logger.error(f"Error explaining candle pattern: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error explaining candle pattern: {str(e)}")

# Log when the application is ready
@app.on_event("startup")
async def startup_event():
    logger.info("Pattern detector service started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Pattern detector service stopped.") 