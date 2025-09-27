#!/usr/bin/env python3
"""
Working startup script - handles all import issues
"""

import os
import sys
import subprocess

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    
    packages = [
        "numpy",
        "gymnasium",  # This is the key fix - use gymnasium not gym
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
    """Test if environment works"""
    print("\nTesting environment...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Test basic imports
        import numpy as np
        print("✓ numpy")
        
        import gymnasium as gym
        print("✓ gymnasium")
        
        import networkx as nx
        print("✓ networkx")
        
        # Test environment import
        from env.wrappers import BusDispatchEnv
        print("✓ BusDispatchEnv")
        
        # Test environment creation
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,
            max_episode_time=60.0,
            seed=42
        )
        print("✓ Environment creation")
        
        # Test reset
        obs = env.reset()
        print(f"✓ Environment reset (obs shape: {obs.shape})")
        
        # Test step
        action = np.random.randint(0, 4, size=env.num_buses)
        obs, reward, done, info = env.step(action)
        print(f"✓ Environment step (reward: {reward})")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_demo():
    """Run a simple demo"""
    print("\nRunning demo...")
    
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
        
        print("Running simulation...")
        for step in range(100):  # 50 seconds
            action = np.random.randint(0, 4, size=env.num_buses)
            obs, reward, done, info = env.step(action)
            total_reward += reward
            
            if step % 20 == 0:
                print(f"Step {step}: Reward = {reward:.2f}, Total = {total_reward:.2f}")
            
            if done:
                break
        
        # Show results
        print(f"\nFinal Results:")
        print(f"Total Reward: {total_reward:.2f}")
        print(f"Simulation Time: {env.current_time:.1f} minutes")
        
        if 'rl_stats' in info:
            print(f"RL Avg Wait: {info['rl_stats']['avg_wait']:.2f} minutes")
        if 'baseline_stats' in info:
            print(f"Baseline Avg Wait: {info['baseline_stats']['avg_wait']:.2f} minutes")
        
        return True
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("=" * 50)
    print("BUS DISPATCH RL - WORKING STARTUP")
    print("=" * 50)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Install packages
    install_requirements()
    
    # Test environment
    if not test_environment():
        print("✗ Environment test failed")
        return 1
    
    # Run demo
    if not run_demo():
        print("✗ Demo failed")
        return 1
    
    print("\n✓ Everything is working!")
    print("You can now run the full system with:")
    print("  python start_simple.py  # For web server")
    print("  python run_demo_simple.py  # For console demo")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
