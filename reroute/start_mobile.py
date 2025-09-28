#!/usr/bin/env python3
"""
Start mobile-optimized server with Manhattan grid
"""

import os
import sys
import subprocess
import time

def main():
    """Start mobile server"""
    print("=" * 50)
    print("STARTING MOBILE BUS DISPATCH RL SERVER")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    print("✓ Mobile-optimized server with Manhattan grid")
    print("✓ Simplified architecture for Android deployment")
    print("✓ Real-time bus tracking on grid map")
    print("✓ Server: http://localhost:8000")
    print("✓ Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Change to server directory and start mobile server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_mobile.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
