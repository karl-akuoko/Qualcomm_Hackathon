#!/usr/bin/env python3
"""
Test the server fix
"""

import os
import sys
import subprocess
import time

def main():
    """Test the fixed server"""
    print("=" * 50)
    print("TESTING FIXED SERVER")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    print("✓ Testing server with fixed step unpacking...")
    
    try:
        # Change to server directory and start fixed server
        os.chdir('server')
        print("✓ Starting server...")
        subprocess.run([sys.executable, 'fastapi_server_integrated.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
