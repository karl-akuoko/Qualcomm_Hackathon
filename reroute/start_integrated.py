#!/usr/bin/env python3
"""
Start integrated server with training and backend integration
"""

import os
import sys
import subprocess
import time
import signal

def kill_process_on_port(port=8000):
    """Kill any process using the specified port"""
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"✓ Killing process {pid} on port {port}")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except (ProcessLookupError, ValueError):
                        pass
            print(f"✓ Cleared port {port}")
        else:
            print(f"✓ Port {port} is already free")
            
    except FileNotFoundError:
        print(f"⚠ Cannot check port {port} status")
    except Exception as e:
        print(f"⚠ Error checking port {port}: {e}")

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'stable_baselines3', 'gymnasium', 
        'numpy', 'torch', 'onnx', 'onnxruntime'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("✗ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall with: pip install " + " ".join(missing_packages))
        return False
    
    print("✓ All required packages are installed")
    return True

def main():
    """Start integrated server"""
    print("=" * 60)
    print("STARTING INTEGRATED BUS DISPATCH RL SERVER")
    print("=" * 60)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Check dependencies
    print("🔧 Checking dependencies...")
    if not check_dependencies():
        print("✗ Please install missing dependencies first")
        return 1
    
    # Kill any existing server
    print("🔧 Checking for existing servers...")
    kill_process_on_port(8000)
    time.sleep(2)
    
    # Check if training files exist
    print("🔧 Checking training setup...")
    if not os.path.exists('train_working.py'):
        print("✗ Training script not found")
        return 1
    
    if not os.path.exists('server/fastapi_server_integrated.py'):
        print("✗ Integrated server not found")
        return 1
    
    print("✓ All components found")
    
    print("\n🚀 Starting integrated server...")
    print("✓ Server: http://localhost:8000")
    print("✓ Dashboard: http://localhost:8000")
    print("✓ Training: Available via dashboard")
    print("✓ RL Mode: Will be available after training")
    print("✓ Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Change to server directory and start integrated server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_server_integrated.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
