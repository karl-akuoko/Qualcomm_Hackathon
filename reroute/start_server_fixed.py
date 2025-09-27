#!/usr/bin/env python3
"""
Start the web server with dashboard
"""

import os
import sys
import subprocess
import time

def main():
    """Start the server"""
    print("=" * 50)
    print("STARTING BUS DISPATCH RL SERVER")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Check if server file exists
    if not os.path.exists('server/fastapi_server.py'):
        print("✗ Server file not found")
        return 1
    
    print("✓ Starting server on http://localhost:8000")
    print("✓ Dashboard will be available at http://localhost:8000")
    print("✓ Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Change to server directory and start
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_server.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
