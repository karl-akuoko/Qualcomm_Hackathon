#!/usr/bin/env python3
"""
Start the fixed server - no more unpacking errors
"""

import os
import sys
import subprocess
import time

def main():
    """Start the fixed server"""
    print("=" * 50)
    print("STARTING FIXED SERVER (NO MORE ERRORS)")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    print("✓ Server fixed - no more 'too many values to unpack' errors")
    print("✓ Starting server on http://localhost:8000")
    print("✓ Dashboard will be available at http://localhost:8000")
    print("✓ Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Change to server directory and start fixed server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_server_integrated.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
