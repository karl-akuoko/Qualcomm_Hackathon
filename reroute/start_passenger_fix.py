#!/usr/bin/env python3
"""
Start server with passenger boarding fixes
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
    """Start server with passenger boarding fixes"""
    print("=" * 60)
    print("STARTING SERVER WITH PASSENGER BOARDING FIXES")
    print("=" * 60)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Kill any existing servers
    print("🔧 Killing existing servers...")
    kill_port_8000()
    time.sleep(2)
    
    print("✓ Starting server with passenger boarding fixes")
    print("✓ Server: http://localhost:8000")
    print("✓ Enhanced passenger boarding mechanics")
    print("✓ Better wait time calculation")
    print("✓ Improved bus routing logic")
    print("✓ Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Change to server directory and start passenger fix server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_passenger_fix.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
