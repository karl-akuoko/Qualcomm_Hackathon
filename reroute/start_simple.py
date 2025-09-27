#!/usr/bin/env python3
"""
Simple startup script for Bus Dispatch RL MVP
Just run this to get everything working
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path

def check_dependencies():
    """Check if basic dependencies are available"""
    try:
        import numpy
        import fastapi
        import uvicorn
        print("✓ Basic dependencies available")
        return True
    except ImportError as e:
        print(f"✗ Missing dependencies: {e}")
        print("Please run: pip install numpy fastapi uvicorn stable-baselines3 torch")
        return False

def start_server():
    """Start the FastAPI server"""
    print("Starting server...")
    
    # Change to server directory
    os.chdir('server')
    
    # Start server
    try:
        subprocess.run([sys.executable, 'fastapi_server.py'], check=True)
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Server error: {e}")

def main():
    """Main startup function"""
    print("=" * 50)
    print("BUS DISPATCH RL - SIMPLE STARTUP")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check if we're in the right directory
    if not Path('env/wrappers.py').exists():
        print("✗ Please run this from the reroute directory")
        return 1
    
    print("✓ Directory structure looks good")
    
    # Start server
    print("\nStarting server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
