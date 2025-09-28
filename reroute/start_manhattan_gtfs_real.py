#!/usr/bin/env python3
"""
Start Manhattan Bus Dispatch Server with Real GTFS Data from gtfs_m folder
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
    required_packages = ['fastapi', 'uvicorn', 'websockets', 'numpy', 'pydantic', 'pandas']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            return False
    return True

def main():
    print("🗽 MANHATTAN BUS DISPATCH SYSTEM - REAL GTFS DATA")
    print("=" * 65)
    print("🗺️ Real Manhattan Bus Stops from MTA GTFS")
    print("📍 Actual MTA Routes & Stops")
    print("🎯 Scaled Up User Activity")
    print("🚌 Real Bus Movement with GTFS Data")
    print("=" * 65)
    
    # Kill existing servers
    kill_existing_servers()
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Missing required packages. Please install them first.")
        return
    
    print("\n🚌 STARTING REAL GTFS SERVER")
    print("=" * 40)
    print("🚌 Starting Manhattan Bus Dispatch Server with Real GTFS Data...")
    print("✓ Server: http://localhost:8000")
    print("✓ Real Data: MTA GTFS from gtfs_m folder")
    print("✓ Scaled Users: Increased passenger generation")
    print("✓ Bus Routes: Real MTA routes with actual stops")
    print("✓ Press Ctrl+C to stop")
    print("=" * 40)
    
    # Start the server
    try:
        os.chdir(os.path.dirname(__file__))
        subprocess.run([sys.executable, 'server/fastapi_manhattan_gtfs_real.py'], check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
    finally:
        print("✅ Manhattan system with real GTFS data stopped")

if __name__ == "__main__":
    main()
