#!/usr/bin/env python3
"""
Startup script for Simple Manhattan Street System
"""

import os
import sys
import subprocess
import time

def kill_existing_servers():
    """Kill any existing servers on port 8000"""
    print("🔧 Killing existing servers...")
    try:
        # Find processes using port 8000
        result = subprocess.run(['lsof', '-ti:8000'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"✓ Killing process {pid} on port 8000")
                    subprocess.run(['kill', '-9', pid], capture_output=True)
                    time.sleep(0.5)
    except Exception as e:
        print(f"⚠️ Error killing processes: {e}")
    
    print("✓ Port 8000 cleared")

def check_dependencies():
    """Check required dependencies"""
    print("📦 Checking dependencies...")
    required_packages = ['fastapi', 'uvicorn', 'websockets', 'numpy', 'pandas']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} not found")
            return False
    
    return True

def main():
    print("🗽 MANHATTAN BUS DISPATCH SYSTEM - SIMPLE STREETS")
    print("============================================================")
    print("🗺️ Street Grid System")
    print("🚌 Buses Only on Streets")
    print("📍 No Parks or Water")
    print("============================================================")
    
    # Kill existing servers
    kill_existing_servers()
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Missing dependencies. Please install required packages.")
        return
    
    print("\n🚌 STARTING SIMPLE STREET SERVER")
    print("========================================")
    print("🚌 Starting Manhattan Bus Dispatch Server with Simple Streets...")
    print("✓ Server: http://localhost:8000")
    print("✓ Street Grid: 12 avenues x 200 streets")
    print("✓ Buses Only: Move on actual streets")
    print("✓ No Parks: Buses cannot go through parks")
    print("✓ No Water: Buses cannot go over water")
    print("✓ Press Ctrl+C to stop")
    print("========================================")
    
    try:
        # Start the server
        os.chdir(os.path.dirname(__file__))
        subprocess.run([sys.executable, 'server/fastapi_manhattan_simple_streets.py'], check=True)
    except KeyboardInterrupt:
        print("\n✅ Simple street system stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
