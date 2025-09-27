#!/usr/bin/env python3
"""
Start server on any available port
"""

import os
import sys
import subprocess
import socket

def find_free_port():
    """Find a free port starting from 8000"""
    for port in range(8000, 8010):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return 8000  # Fallback

def main():
    """Start server on available port"""
    print("=" * 50)
    print("STARTING BUS DISPATCH RL SERVER")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Find free port
    port = find_free_port()
    
    print(f"✓ Starting server on http://localhost:{port}")
    print(f"✓ Dashboard will be available at http://localhost:{port}")
    print("✓ Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Change to server directory and start with custom port
        os.chdir('server')
        
        # Modify the server to use the found port
        with open('fastapi_server.py', 'r') as f:
            content = f.read()
        
        # Replace the port in the uvicorn.run call
        if 'uvicorn.run(app, host="0.0.0.0", port=8000)' in content:
            content = content.replace('port=8000', f'port={port}')
            with open('fastapi_server.py', 'w') as f:
                f.write(content)
        
        subprocess.run([sys.executable, 'fastapi_server.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
