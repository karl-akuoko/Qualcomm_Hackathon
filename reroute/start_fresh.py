#!/usr/bin/env python3
"""
Start server fresh - kill any existing server first
"""

import os
import sys
import subprocess
import signal
import time

def kill_process_on_port(port=8000):
    """Kill any process using the specified port"""
    try:
        # Find process using the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"✓ Killing process {pid} on port {port}")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)  # Give it time to die
                        # Force kill if still running
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass  # Already dead
                    except (ProcessLookupError, ValueError):
                        pass  # Process already dead or invalid PID
            print(f"✓ Cleared port {port}")
        else:
            print(f"✓ Port {port} is already free")
            
    except FileNotFoundError:
        # lsof not available, try netstat
        try:
            result = subprocess.run(['netstat', '-tulpn'], 
                                  capture_output=True, text=True)
            if f':{port}' in result.stdout:
                print(f"⚠ Port {port} appears to be in use but can't kill process")
                print("⚠ You may need to manually kill the process")
        except FileNotFoundError:
            print(f"⚠ Cannot check port {port} status")
    except Exception as e:
        print(f"⚠ Error checking port {port}: {e}")

def main():
    """Start server fresh"""
    print("=" * 50)
    print("STARTING BUS DISPATCH RL SERVER (FRESH)")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Kill any existing server
    print("🔧 Checking for existing servers...")
    kill_process_on_port(8000)
    
    # Wait a moment for port to be released
    time.sleep(2)
    
    print("✓ Starting fresh server on http://localhost:8000")
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
