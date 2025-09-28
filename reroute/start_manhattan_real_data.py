#!/usr/bin/env python3
"""
Start Manhattan Bus Dispatch System - Real Data
Uses actual bus stops and image processing for road network
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def kill_existing_servers():
    """Kill any existing servers on port 8000"""
    print("🔧 Killing existing servers...")
    
    try:
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
    """Check if required dependencies are installed"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'websockets',
        'numpy',
        'pydantic',
        'opencv-python',
        'scipy',
        'scikit-image'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'scikit-image':
                import skimage
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} (missing)")
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✓ Installed {package}")
            except subprocess.CalledProcessError:
                print(f"✗ Failed to install {package}")
                return False
    
    return True

def test_real_data():
    """Test real Manhattan data loading"""
    print("🗽 Testing real Manhattan data...")
    
    try:
        # Test loading the real data
        geojson_path = os.path.join(os.path.dirname(__file__), 'UI_data', 'sample_manhattan_stops.geojson')
        
        if not os.path.exists(geojson_path):
            print(f"✗ Real data file not found: {geojson_path}")
            return False
        
        import json
        with open(geojson_path, 'r') as f:
            data = json.load(f)
        
        stops = data['features']
        print(f"✓ Loaded {len(stops)} real Manhattan stops")
        
        # Show some stops
        for i, stop in enumerate(stops[:3]):
            props = stop['properties']
            print(f"  📍 {props['stop_name']}: {props['routes_served_csv']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing real data: {e}")
        return False

def start_real_data_server():
    """Start the real data server"""
    print("🚌 Starting Manhattan Bus Dispatch Server with Real Data...")
    
    try:
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        server_script = "server/fastapi_manhattan_real_data.py"
        
        print(f"✓ Server: http://localhost:8000")
        print(f"✓ Real Data: Actual Manhattan bus stops")
        print(f"✓ Road Network: Image processing")
        print(f"✓ Bus Routes: Based on real MTA data")
        print(f"✓ Press Ctrl+C to stop")
        print("=" * 50)
        
        subprocess.run([sys.executable, server_script])
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"✗ Error starting server: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🗽 MANHATTAN BUS DISPATCH SYSTEM - REAL DATA")
    print("=" * 50)
    print("🗺️ Real Manhattan Bus Stops")
    print("📍 Road Network Processing")
    print("🎯 Actual Bus Routes")
    print("🚌 Image Processing for Roads")
    print("=" * 50)
    
    # Kill existing servers
    kill_existing_servers()
    
    # Check dependencies
    if not check_dependencies():
        print("✗ Failed to install dependencies")
        return False
    
    # Test real data
    if not test_real_data():
        print("✗ Failed to test real data")
        return False
    
    # Start server
    print("\n🚌 STARTING REAL DATA SERVER")
    print("=" * 30)
    if not start_real_data_server():
        print("✗ Failed to start server")
        return False
    
    print("✅ Manhattan system with real data started successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
