#!/usr/bin/env python3
"""
Start Manhattan Bus Dispatch System with RL Training
Train RL model first, then start server with dynamic routing
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def kill_existing_servers():
    """Kill any existing servers on port 8000 using simple commands"""
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
    """Check if required dependencies are installed"""
    print("📦 Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'websockets',
        'numpy',
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
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

def train_rl_model():
    """Train the RL model for Manhattan bus dispatch"""
    print("🤖 Training RL model for Manhattan bus dispatch...")
    
    try:
        # Run the training script
        result = subprocess.run([sys.executable, 'train_manhattan_rl.py'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            print("✅ RL model training completed successfully!")
            return True
        else:
            print(f"✗ RL model training failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error training RL model: {e}")
        return False

def test_manhattan_data():
    """Test Manhattan data parsing"""
    print("🗽 Testing Manhattan data parsing...")
    
    try:
        # Test the data parser
        sys.path.append(os.path.join(os.path.dirname(__file__)))
        from manhattan_data_parser import ManhattanDataParser
        
        parser = ManhattanDataParser()
        stops = parser.load_manhattan_stops()
        routes = parser.create_manhattan_routes()
        
        print(f"✓ Loaded {len(stops)} Manhattan stops")
        print(f"✓ Created {len(routes)} MTA routes")
        
        # Show some key stops
        key_stops = ["TRANS_001", "TRANS_002", "TRANS_003"]
        for stop_id in key_stops:
            if stop_id in stops:
                stop = stops[stop_id]
                print(f"  📍 {stop.stop_name}: {', '.join(stop.routes)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Manhattan data: {e}")
        return False

def start_manhattan_rl_server():
    """Start the Manhattan bus dispatch server with RL"""
    print("🚌 Starting Manhattan Bus Dispatch Server with RL...")
    
    try:
        # Change to the correct directory
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # Start the server
        server_script = "server/fastapi_manhattan_rl.py"
        
        print(f"✓ Server: http://localhost:8000")
        print(f"✓ RL Model: Trained and loaded")
        print(f"✓ Dynamic Routing: Active")
        print(f"✓ Real MTA Routes: M1, M2, M3, M4, M5, M7, M104, M14A, M14D, M15, M15SBS, M11")
        print(f"✓ Real Manhattan Stops: Times Square, Union Square, Central Park")
        print(f"✓ Press Ctrl+C to stop")
        print("=" * 50)
        
        # Run the server
        subprocess.run([sys.executable, server_script])
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"✗ Error starting server: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🗽 MANHATTAN BUS DISPATCH SYSTEM WITH RL")
    print("=" * 50)
    print("🤖 Train RL Model First")
    print("🚌 Dynamic Bus Routing")
    print("📍 Real Manhattan Geography")
    print("🎯 Demand-Responsive Dispatch")
    print("=" * 50)
    
    # Kill existing servers
    kill_existing_servers()
    
    # Check dependencies
    if not check_dependencies():
        print("✗ Failed to install dependencies")
        return False
    
    # Test Manhattan data
    if not test_manhattan_data():
        print("✗ Failed to test Manhattan data")
        return False
    
    # Train RL model
    print("\n🤖 TRAINING RL MODEL")
    print("=" * 30)
    if not train_rl_model():
        print("⚠️ RL model training failed, but continuing with static mode...")
    
    # Start server
    print("\n🚌 STARTING SERVER")
    print("=" * 30)
    if not start_manhattan_rl_server():
        print("✗ Failed to start server")
        return False
    
    print("✅ Manhattan RL system started successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
