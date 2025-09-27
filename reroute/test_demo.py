#!/usr/bin/env python3
"""
Simple test script to verify the bus routing demo is working.
"""

import requests
import time
import json


def test_api():
    """Test the API endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Bus Routing API")
    print("=" * 40)
    
    # Test 1: Get status
    print("\n1. Testing status endpoint...")
    try:
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            print("✅ Status endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Status endpoint error: {e}")
        return False
    
    # Test 2: Reset simulation
    print("\n2. Testing reset endpoint...")
    try:
        response = requests.post(f"{base_url}/reset", json={"seed": 42})
        if response.status_code == 200:
            print("✅ Reset endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Reset endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Reset endpoint error: {e}")
        return False
    
    # Test 3: Start simulation
    print("\n3. Testing start endpoint...")
    try:
        response = requests.post(f"{base_url}/start")
        if response.status_code == 200:
            print("✅ Start endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Start endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Start endpoint error: {e}")
        return False
    
    # Test 4: Get KPIs
    print("\n4. Testing KPIs endpoint...")
    try:
        response = requests.get(f"{base_url}/kpis")
        if response.status_code == 200:
            print("✅ KPIs endpoint working")
            kpis = response.json()
            print(f"   Current KPIs: {kpis.get('current', {})}")
        else:
            print(f"❌ KPIs endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ KPIs endpoint error: {e}")
        return False
    
    # Test 5: Switch to RL mode
    print("\n5. Testing mode switch...")
    try:
        response = requests.post(f"{base_url}/mode", json={"mode": "rl"})
        if response.status_code == 200:
            print("✅ Mode switch working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Mode switch failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Mode switch error: {e}")
        return False
    
    # Test 6: Trigger stress test
    print("\n6. Testing stress test...")
    try:
        response = requests.post(f"{base_url}/stress", json={"type": "closure"})
        if response.status_code == 200:
            print("✅ Stress test working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Stress test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Stress test error: {e}")
        return False
    
    # Test 7: Run simulation for a few seconds
    print("\n7. Running simulation for 10 seconds...")
    time.sleep(10)
    
    # Test 8: Get final KPIs
    print("\n8. Getting final KPIs...")
    try:
        response = requests.get(f"{base_url}/kpis")
        if response.status_code == 200:
            print("✅ Final KPIs retrieved")
            kpis = response.json()
            current = kpis.get('current', {})
            if current:
                print(f"   Avg Wait: {current.get('avg_wait', 0):.2f}s")
                print(f"   P90 Wait: {current.get('p90_wait', 0):.2f}s")
                print(f"   Load Std: {current.get('load_std', 0):.2f}")
                print(f"   Active Riders: {current.get('active_riders', 0)}")
            else:
                print("   No KPI data available yet")
        else:
            print(f"❌ Final KPIs failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Final KPIs error: {e}")
    
    # Test 9: Stop simulation
    print("\n9. Stopping simulation...")
    try:
        response = requests.post(f"{base_url}/stop")
        if response.status_code == 200:
            print("✅ Stop endpoint working")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Stop endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Stop endpoint error: {e}")
    
    print("\n🎉 API testing completed!")
    print("\nNext steps:")
    print("1. Open http://localhost:3000 for the web dashboard")
    print("2. Or visit http://localhost:8000/docs for API documentation")
    print("3. The simulation is ready for demonstration!")
    
    return True


if __name__ == "__main__":
    success = test_api()
    if success:
        print("\n✅ All tests passed! Demo is ready.")
    else:
        print("\n❌ Some tests failed. Check the server logs.")