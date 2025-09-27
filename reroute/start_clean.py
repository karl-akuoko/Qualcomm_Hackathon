#!/usr/bin/env python3
"""
Start the clean server with working dashboard
"""

import os
import sys
import subprocess

def main():
    """Start the clean server"""
    print("=" * 50)
    print("STARTING BUS DISPATCH RL SERVER (CLEAN)")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Check if clean server file exists
    if not os.path.exists('server/fastapi_server_clean.py'):
        print("✗ Clean server file not found")
        return 1
    
    print("✓ Starting clean server on http://localhost:8000")
    print("✓ Dashboard will be available at http://localhost:8000")
    print("✓ Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Change to server directory and start clean server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_server_clean.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
