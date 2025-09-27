#!/usr/bin/env python3
"""
Force start server - kill existing and start fresh
"""

import os
import sys
import subprocess
import time

def main():
    """Force start server"""
    print("=" * 50)
    print("FORCE STARTING BUS DISPATCH RL SERVER")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    print("🔧 Killing any existing servers...")
    
    # Try to kill processes on port 8000
    try:
        # Method 1: Use lsof to find and kill
        result = subprocess.run(['lsof', '-ti', ':8000'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"✓ Killing process {pid}")
                    subprocess.run(['kill', '-9', pid], capture_output=True)
    except:
        pass
    
    # Wait for port to be released
    print("⏳ Waiting for port to be released...")
    time.sleep(3)
    
    print("✓ Starting server on http://localhost:8000")
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
