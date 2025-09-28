#!/usr/bin/env python3
"""
Test passenger boarding mechanics
"""

import os
import sys
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def test_passenger_boarding():
    """Test if passengers are actually boarding buses"""
    
    print("=" * 50)
    print("TESTING PASSENGER BOARDING")
    print("=" * 50)
    
    # Create environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=120.0,  # 2 hour test
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
    
    # Check initial bus loads
    for bus in state['buses']:
        print(f"  - Bus {bus['id']}: pos=({bus['x']}, {bus['y']}), load={bus['load']}/{bus['capacity']}, moving={bus['is_moving']}")
    
    # Check initial stop queues
    total_waiting = 0
    for stop in state['stops']:
        if stop['queue_len'] > 0:
            total_waiting += stop['queue_len']
            print(f"  - Stop {stop['id']}: {stop['queue_len']} waiting")
    
    print(f"  - Total passengers waiting: {total_waiting}")
    
    # Run simulation and track passenger boarding
    print("\nRunning simulation to test passenger boarding...")
    passengers_boarding = 0
    max_bus_load = 0
    
    for step in range(20):  # 20 steps = 20 minutes
        print(f"\n--- Step {step + 1} ---")
        
        # Take action (continue for all buses)
        actions = [0] * env.num_buses
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        # Get state
        state = env.get_system_state()
        print(f"Time: {state['time']:.1f}")
        
        # Check bus loads and passenger boarding
        step_boarding = 0
        for bus in state['buses']:
            if bus['load'] > 0:
                step_boarding += bus['load']
                max_bus_load = max(max_bus_load, bus['load'])
                print(f"  Bus {bus['id']}: pos=({bus['x']:.1f}, {bus['y']:.1f}), load={bus['load']}/{bus['capacity']}, moving={bus['is_moving']}")
        
        if step_boarding > 0:
            passengers_boarding += step_boarding
            print(f"  ✓ {step_boarding} passengers on buses!")
        
        # Check stop queues
        total_waiting = 0
        for stop in state['stops']:
            if stop['queue_len'] > 0:
                total_waiting += stop['queue_len']
        
        print(f"  - Passengers waiting: {total_waiting}")
        
        # Check KPIs
        if state['kpi']:
            print(f"  - RL Wait: {state['kpi']['avg_wait']:.1f}")
        if state['baseline_kpi']:
            print(f"  - Baseline Wait: {state['baseline_kpi']['avg_wait']:.1f}")
        
        if done or truncated:
            print("Episode ended!")
            break
    
    print(f"\n" + "=" * 50)
    print("PASSENGER BOARDING TEST RESULTS")
    print("=" * 50)
    print(f"Total passengers that boarded: {passengers_boarding}")
    print(f"Maximum bus load observed: {max_bus_load}")
    print(f"Average passengers per bus: {passengers_boarding / len(state['buses']):.1f}")
    
    if passengers_boarding > 0:
        print("✅ SUCCESS: Passengers are boarding buses!")
    else:
        print("❌ PROBLEM: No passengers boarded buses!")
        print("   This indicates an issue with the passenger boarding mechanics.")
    
    return passengers_boarding > 0

if __name__ == "__main__":
    test_passenger_boarding()
