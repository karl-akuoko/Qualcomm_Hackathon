#!/usr/bin/env python3
"""
Start server on any available port
"""

import os
import sys
import subprocess
import socket

def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

def main():
    """Start server on any available port"""
    print("=" * 50)
    print("STARTING BUS DISPATCH RL SERVER (ANY PORT)")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Find free port
    port = find_free_port()
    if port is None:
        print("✗ No free ports available")
        return 1
    
    print(f"✓ Found free port: {port}")
    print(f"✓ Starting server on http://localhost:{port}")
    print(f"✓ Dashboard will be available at http://localhost:{port}")
    print("✓ Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Change to server directory and start server
        os.chdir('server')
        
        # Modify the server to use the found port
        with open('fastapi_server_clean.py', 'r') as f:
            content = f.read()
        
        # Replace the port in the uvicorn.run call
        content = content.replace('port=8000', f'port={port}')
        
        with open('fastapi_server_temp.py', 'w') as f:
            f.write(content)
        
        subprocess.run([sys.executable, 'fastapi_server_temp.py'])
        
        # Clean up temp file
        if os.path.exists('fastapi_server_temp.py'):
            os.remove('fastapi_server_temp.py')
            
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
