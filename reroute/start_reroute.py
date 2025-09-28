#!/usr/bin/env python3
"""
Startup script for Manhattan reRoute Bus Dispatch System
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
    print("🗽 MANHATTAN BUS DISPATCH SYSTEM - reRoute ALGORITHM")
    print("============================================================")
    print("🗺️ Road Network Constraints")
    print("🤖 Reinforcement Learning")
    print("🚌 Dynamic Route Optimization")
    print("============================================================")
    
    # Kill existing servers
    kill_existing_servers()
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Missing dependencies. Please install required packages.")
        return
    
    print("\n🚌 STARTING reRoute SERVER")
    print("========================================")
    print("🚌 Starting Manhattan Bus Dispatch Server with reRoute Algorithm...")
    print("✓ Server: http://localhost:8000")
    print("✓ Road Constraints: Only permissible road positions")
    print("✓ RL Algorithm: Dynamic route optimization")
    print("✓ Demand-Based Routing: Adapts to passenger demand")
    print("✓ Traffic Avoidance: Avoids congested areas")
    print("✓ Press Ctrl+C to stop")
    print("========================================")
    
    try:
        # Start the server
        os.chdir(os.path.dirname(__file__))
        subprocess.run([sys.executable, 'server/fastapi_manhattan_reroute.py'], check=True)
    except KeyboardInterrupt:
        print("\n✅ Manhattan reRoute system stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
