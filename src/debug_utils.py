"""Debug utilities for the Document QA RAG Agent."""

import os
import sys
import traceback
from typing import Any, Dict, Optional
from datetime import datetime


def debug_print(message: str, level: str = "INFO") -> None:
    """Print debug message with timestamp if debug mode is enabled."""
    if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{level}] {message}")


def debug_exception(e: Exception, context: str = "") -> None:
    """Print detailed exception information in debug mode."""
    if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
        print(f"\n{'='*50}")
        print(f"🐛 EXCEPTION in {context}")
        print(f"Type: {type(e).__name__}")
        print(f"Message: {str(e)}")
        print(f"Traceback:")
        traceback.print_exc()
        print(f"{'='*50}\n")


def debug_session_state(st_session_state: Any) -> None:
    """Print current Streamlit session state in debug mode."""
    if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
        print(f"\n{'='*30} SESSION STATE {'='*30}")
        for key, value in st_session_state.items():
            if key.startswith("_"):  # Skip internal Streamlit keys
                continue
            try:
                value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                print(f"{key}: {value_str}")
            except Exception:
                print(f"{key}: <unprintable>")
        print(f"{'='*75}\n")


def debug_api_call(endpoint: str, payload: Optional[Dict] = None, response: Optional[Dict] = None) -> None:
    """Debug API calls and responses."""
    if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
        print(f"\n🌐 API CALL: {endpoint}")
        if payload:
            print(f"📤 Payload: {payload}")
        if response:
            print(f"📥 Response: {response}")
        print()


def setup_debug_environment() -> bool:
    """Setup debug environment and return True if debugging is enabled."""
    debug_enabled = os.getenv("DEBUG_STREAMLIT", "false").lower() == "true"
    
    if debug_enabled:
        print("🐛 Debug mode enabled")
        print(f"🐍 Python version: {sys.version}")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"📦 Python path: {sys.path[:3]}...")  # Show first 3 paths
        
        # Add current directory to Python path if not already there
        if "." not in sys.path:
            sys.path.insert(0, ".")
            print("📌 Added current directory to Python path")
    
    return debug_enabled


class DebugContext:
    """Context manager for debugging code blocks."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
            self.start_time = datetime.now()
            debug_print(f"🚀 Starting: {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
            if exc_type is not None:
                debug_exception(exc_val, self.name)
            else:
                duration = datetime.now() - self.start_time
                debug_print(f"✅ Completed: {self.name} ({duration.total_seconds():.3f}s)")


# Decorator for debugging functions
def debug_function(func):
    """Decorator to add debug logging to functions."""
    def wrapper(*args, **kwargs):
        if os.getenv("DEBUG_STREAMLIT", "false").lower() == "true":
            debug_print(f"🔧 Calling: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                debug_print(f"✅ Completed: {func.__name__}")
                return result
            except Exception as e:
                debug_exception(e, func.__name__)
                raise
        else:
            return func(*args, **kwargs)
    return wrapper