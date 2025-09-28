#!/usr/bin/env python3
"""
Test the simulation to see what's happening with buses
"""

import os
import sys
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def test_simulation():
    """Test the simulation step by step"""
    
    print("=" * 50)
    print("TESTING SIMULATION")
    print("=" * 50)
    
    # Create environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=60.0,
        seed=42
    )
    
    print("✓ Environment created")
    
    # Reset environment
    obs, info = env.reset()
    print(f"✓ Environment reset, obs shape: {obs.shape}")
    
    # Get initial state
    state = env.get_system_state()
    print(f"✓ Initial state:")
    print(f"  - Time: {state['time']}")
    print(f"  - Buses: {len(state['buses'])}")
    print(f"  - Stops: {len(state['stops'])}")
    
    # Check bus positions
    for bus in state['buses']:
        print(f"  - Bus {bus['id']}: pos=({bus['x']}, {bus['y']}), load={bus['load']}/{bus['capacity']}, moving={bus['is_moving']}")
    
    # Run a few steps
    print("\nRunning simulation steps...")
    for step in range(5):
        print(f"\n--- Step {step + 1} ---")
        
        # Take action (continue for all buses)
        actions = [0] * env.num_buses
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        # Get state
        state = env.get_system_state()
        print(f"Time: {state['time']:.1f}")
        
        # Check bus positions
        for bus in state['buses']:
            print(f"  Bus {bus['id']}: pos=({bus['x']:.1f}, {bus['y']:.1f}), load={bus['load']}/{bus['capacity']}, moving={bus['is_moving']}")
        
        # Check KPIs
        if state['kpi']:
            print(f"  RL Wait: {state['kpi']['avg_wait']:.1f}")
        if state['baseline_kpi']:
            print(f"  Baseline Wait: {state['baseline_kpi']['avg_wait']:.1f}")
        
        if done or truncated:
            print("Episode ended!")
            break
    
    print("\n✓ Simulation test completed")

if __name__ == "__main__":
    test_simulation()
