#!/usr/bin/env python3
"""
Final working startup script - handles all issues
"""

import os
import sys
import subprocess
import time
import threading

def install_packages():
    """Install required packages"""
    print("Installing required packages...")
    
    packages = [
        "numpy",
        "gymnasium",  # Key fix: use gymnasium not gym
        "networkx",
        "matplotlib", 
        "fastapi",
        "uvicorn",
        "websockets",
        "pydantic",
        "stable-baselines3",
        "torch",
        "pandas"
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✓ {package}")
        except subprocess.CalledProcessError:
            print(f"✗ {package} (may already be installed)")

def test_environment():
    """Test environment works"""
    print("\nTesting environment...")
    
    try:
        sys.path.insert(0, os.getcwd())
        
        from env.wrappers import BusDispatchEnv
        import numpy as np
        
        # Create environment
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,
            max_episode_time=60.0,
            seed=42
        )
        
        # Test reset
        obs = env.reset()
        print(f"✓ Environment reset (obs shape: {obs.shape})")
        
        # Test step
        action = np.random.randint(0, 4, size=env.num_buses)
        obs, reward, done, info = env.step(action)
        print(f"✓ Environment step (reward: {reward})")
        
        # Test system state
        state = env.get_system_state()
        print(f"✓ System state (buses: {len(state['buses'])}, stops: {len(state['stops'])})")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_server():
    """Test server imports"""
    print("\nTesting server...")
    
    try:
        sys.path.insert(0, os.getcwd())
        sys.path.insert(0, os.path.join(os.getcwd(), 'server'))
        
        from fastapi_server import app
        print("✓ Server imports work")
        
        return True
        
    except Exception as e:
        print(f"✗ Server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_demo():
    """Run a complete demo"""
    print("\nRunning complete demo...")
    
    try:
        sys.path.insert(0, os.getcwd())
        from env.wrappers import BusDispatchEnv
        import numpy as np
        
        # Create environment
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,
            max_episode_time=120.0,
            seed=42
        )
        
        # Run simulation
        obs = env.reset()
        total_reward = 0
        
        print("Running simulation (2 minutes)...")
        for step in range(240):  # 2 minutes
            action = np.random.randint(0, 4, size=env.num_buses)
            obs, reward, done, info = env.step(action)
            total_reward += reward
            
            if step % 30 == 0:  # Every 15 seconds
                time_min = env.current_time
                rl_wait = info.get('rl_stats', {}).get('avg_wait', 0)
                baseline_wait = info.get('baseline_stats', {}).get('avg_wait', 0)
                print(f"Time {time_min:4.1f}m: RL={rl_wait:5.1f}min, Baseline={baseline_wait:5.1f}min")
            
            if done:
                break
        
        # Final results
        print(f"\nFinal Results:")
        print(f"Total Reward: {total_reward:.2f}")
        print(f"Simulation Time: {env.current_time:.1f} minutes")
        
        if 'rl_stats' in info:
            print(f"RL Avg Wait: {info['rl_stats']['avg_wait']:.2f} minutes")
            print(f"RL Load Std: {info['rl_stats']['load_std']:.2f}")
        
        if 'baseline_stats' in info:
            print(f"Baseline Avg Wait: {info['baseline_stats']['avg_wait']:.2f} minutes")
            print(f"Baseline Load Std: {info['baseline_stats']['load_std']:.2f}")
        
        if 'improvements' in info:
            improvements = info['improvements']
            print(f"\nImprovements:")
            print(f"Wait Time: {improvements.get('avg_wait', 0)*100:.1f}%")
            print(f"Overcrowding: {improvements.get('overcrowd', 0)*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_server():
    """Start the web server"""
    print("\nStarting web server...")
    print("Server will run on http://localhost:8000")
    print("Press Ctrl+C to stop")
    
    try:
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_server.py'])
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Server error: {e}")

def main():
    """Main function"""
    print("=" * 60)
    print("BUS DISPATCH RL - FINAL WORKING STARTUP")
    print("=" * 60)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Install packages
    install_packages()
    
    # Test environment
    if not test_environment():
        print("✗ Environment test failed")
        return 1
    
    # Test server
    if not test_server():
        print("✗ Server test failed")
        return 1
    
    # Run demo
    if not run_demo():
        print("✗ Demo failed")
        return 1
    
    print("\n" + "=" * 60)
    print("✓ EVERYTHING IS WORKING!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. Run demo: python run_demo_simple.py")
    print("2. Start server: python start_final.py --server")
    print("3. View dashboard: http://localhost:8000")
    
    # Check if user wants to start server
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        start_server()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
