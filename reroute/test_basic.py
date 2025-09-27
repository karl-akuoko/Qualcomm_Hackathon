#!/usr/bin/env python3
"""
Basic test - just check if the environment works
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_imports():
    """Test if we can import the main components"""
    print("Testing imports...")
    
    try:
        from env.wrappers import BusDispatchEnv
        print("✓ BusDispatchEnv imported")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_environment():
    """Test basic environment functionality"""
    print("Testing environment...")
    
    try:
        from env.wrappers import BusDispatchEnv
        
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
        print(f"✓ Environment reset. Obs shape: {obs.shape}")
        
        # Test step
        import numpy as np
        action = np.random.randint(0, 4, size=env.num_buses)
        obs, reward, done, info = env.step(action)
        print(f"✓ Environment step. Reward: {reward}")
        
        # Test system state
        state = env.get_system_state()
        print(f"✓ System state. Buses: {len(state['buses'])}, Stops: {len(state['stops'])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run basic tests"""
    print("=" * 40)
    print("BASIC ENVIRONMENT TEST")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        print("Current directory:", os.getcwd())
        return 1
    
    # Test imports
    if not test_imports():
        print("✗ Import test failed")
        return 1
    
    # Test environment
    if not test_environment():
        print("✗ Environment test failed")
        return 1
    
    print("\n✓ All basic tests passed!")
    print("You can now run: python run_demo_simple.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())
