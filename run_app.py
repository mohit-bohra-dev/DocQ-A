#!/usr/bin/env python3
"""
Startup script for the Document QA RAG Agent.
This script helps users run both the FastAPI backend and Streamlit UI.
"""

import subprocess
import sys
import time
import os
import signal
from typing import Optional


def check_port_available(port: int) -> bool:
    """Check if a port is available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False


def start_fastapi_server() -> subprocess.Popen:
    """Start the FastAPI server."""
    print("🚀 Starting FastAPI backend server...")
    
    # Check if port 8000 is available
    if not check_port_available(8000):
        print("⚠️  Port 8000 is already in use. Please stop any existing FastAPI server.")
        print("   You can find and kill the process using: lsof -ti:8000 | xargs kill")
        return None
    
    try:
        # Start FastAPI server
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "src.app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give the server time to start
        time.sleep(3)
        
        # Check if the process is still running
        if process.poll() is None:
            print("✅ FastAPI server started successfully on http://localhost:8000")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Failed to start FastAPI server:")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting FastAPI server: {e}")
        return None


def start_streamlit_app() -> subprocess.Popen:
    """Start the Streamlit application."""
    print("🎨 Starting Streamlit UI...")
    
    # Check if port 8501 is available
    if not check_port_available(8501):
        print("⚠️  Port 8501 is already in use. Please stop any existing Streamlit app.")
        return None

    try:
        # uv run streamlit run streamlit_app.py --server.port 8502 --server.address localhost
        #       Welcome to Streamlit!
        # Start Streamlit app
        process = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run",
                "streamlit_app.py",
                "--server.port", "8501",
                "--server.address", "localhost"
            ]
        )

        # Give Streamlit time to start
        time.sleep(5)
        
        # Check if the process is still running
        if process.poll() is None:
            print("✅ Streamlit UI started successfully on http://localhost:8501")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Failed to start Streamlit app:")
            print(f"   stdout: {stdout.decode()}")
            print(f"   stderr: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting Streamlit app: {e}")
        return None


def main():
    """Main function to start both services."""
    print("📚 Document QA RAG Agent - Startup Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("src/app.py"):
        print("❌ Error: Please run this script from the project root directory")
        print("   Make sure you can see the 'src' folder and 'streamlit_app.py' file")
        sys.exit(1)
    
    # Check if dependencies are installed
    try:
        import fastapi
        import streamlit
        import uvicorn
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("   Please install dependencies with: pip install -e .")
        sys.exit(1)
    
    fastapi_process = None
    streamlit_process = None
    
    try:
        # Start FastAPI server
        fastapi_process = start_fastapi_server()
        if not fastapi_process:
            print("❌ Failed to start FastAPI server. Exiting.")
            sys.exit(1)
        
        # Start Streamlit app
        streamlit_process = start_streamlit_app()
        if not streamlit_process:
            print("❌ Failed to start Streamlit app. Stopping FastAPI server.")
            if fastapi_process:
                fastapi_process.terminate()
            sys.exit(1)
        
        print("\n🎉 Both services started successfully!")
        print("📖 FastAPI Backend: http://localhost:8000")
        print("🎨 Streamlit UI: http://localhost:8501")
        print("\n📋 API Documentation: http://localhost:8000/docs")
        print("\n⏹️  Press Ctrl+C to stop both services")
        
        # Wait for user interrupt
        try:
            while True:
                time.sleep(1)
                # Check if processes are still running
                if fastapi_process.poll() is not None:
                    print("⚠️  FastAPI server stopped unexpectedly")
                    break
                if streamlit_process.poll() is not None:
                    print("⚠️  Streamlit app stopped unexpectedly")
                    break
        except KeyboardInterrupt:
            print("\n🛑 Shutting down services...")
    
    finally:
        # Clean up processes
        if fastapi_process and fastapi_process.poll() is None:
            print("🔄 Stopping FastAPI server...")
            fastapi_process.terminate()
            try:
                fastapi_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                fastapi_process.kill()
        
        if streamlit_process and streamlit_process.poll() is None:
            print("🔄 Stopping Streamlit app...")
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlit_process.kill()
        
        print("✅ All services stopped. Goodbye!")


if __name__ == "__main__":
    main()