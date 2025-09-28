#!/usr/bin/env python3
"""
Check if server is running and show status
"""

import requests
import time

def check_server():
    """Check if server is running"""
    try:
        response = requests.get('http://localhost:8000/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Server is running!")
            print(f"   Mode: {data.get('mode', 'unknown')}")
            print(f"   Buses: {data.get('buses', 0)}")
            print(f"   Stops: {data.get('stops', 0)}")
            print(f"   Connected clients: {data.get('connected_clients', 0)}")
            print(f"   Simulation time: {data.get('simulation_time', 0):.1f}")
            print("\n🌐 Open http://localhost:8000 in your browser")
            return True
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking server status...")
    check_server()
