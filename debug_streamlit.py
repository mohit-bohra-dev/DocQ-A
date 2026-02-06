#!/usr/bin/env python3
"""
Debug startup script for Streamlit app.
This script starts the Streamlit app with debugging enabled.
"""

import os
import subprocess
import sys

def main():
    """Start Streamlit with debugging enabled."""
    print("🐛 Starting Streamlit app in debug mode...")
    print("📍 Debug server will be available on port 5678")
    print("🔗 Streamlit UI will be available on http://localhost:8501")
    print("\n📋 To debug:")
    print("1. Start this script")
    print("2. In VS Code, use 'Run and Debug' -> 'Debug Streamlit App'")
    print("3. Or attach any Python debugger to localhost:5678")
    print("\n" + "="*50)
    
    # Set debug environment variable
    env = os.environ.copy()
    env["DEBUG_STREAMLIT"] = "true"
    
    # Start Streamlit with debug mode
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--server.headless", "true"
        ], env=env, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Debug session stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()