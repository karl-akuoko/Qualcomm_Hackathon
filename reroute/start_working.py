#!/usr/bin/env python3
"""
Start server with working data structures
"""

import os
import sys
import subprocess
import time
import signal

def kill_port_8000():
    """Kill any processes using port 8000"""
    try:
        result = subprocess.run(['lsof', '-ti', ':8000'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"✓ Killing process {pid} on port 8000")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except (ProcessLookupError, ValueError):
                        pass
            print("✓ Port 8000 cleared")
        else:
            print("✓ Port 8000 is already free")
            
    except FileNotFoundError:
        print("⚠ Cannot check port 8000 status")
    except Exception as e:
        print(f"⚠ Error checking port 8000: {e}")

def main():
    """Start server with working data structures"""
    print("=" * 60)
    print("STARTING SERVER WITH WORKING DATA STRUCTURES")
    print("=" * 60)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Kill any existing servers
    print("🔧 Killing existing servers...")
    kill_port_8000()
    time.sleep(2)
    
    print("✓ Starting server with working data structures")
    print("✓ Server: http://localhost:8000")
    print("✓ Fixed Stop class with total_wait_time attribute")
    print("✓ Fixed bus object access in environment")
    print("✓ Using environment's get_system_state method")
    print("✓ Proper passenger boarding mechanics")
    print("✓ Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Change to server directory and start working server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_working.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())