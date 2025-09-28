#!/usr/bin/env python3
"""
Simple debug of passenger boarding
"""

import os
import sys
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def debug_simple():
    """Simple debug of the simulation"""
    
    print("🔍 SIMPLE DEBUG OF BUS DISPATCH")
    print("=" * 40)
    
    # Create environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=60.0,
        seed=42
    )
    
    # Reset environment
    obs, info = env.reset()
    
    print(f"Environment created:")
    print(f"  Buses: {len(env.bus_fleet.buses)}")
    print(f"  Stops: {len(env.city_grid.stops)}")
    
    # Check initial bus positions
    print(f"\nInitial bus positions:")
    for bus in env.bus_fleet.buses:
        print(f"  Bus {bus.id}: at ({bus.x:.1f}, {bus.y:.1f}) with {bus.load} passengers")
    
    # Check initial stops
    print(f"\nInitial stop states:")
    for stop in env.city_grid.stops:
        if stop.queue_len > 0:
            print(f"  Stop {stop.id}: {stop.queue_len} passengers waiting")
    
    # Run a few steps
    print(f"\nRunning 10 steps...")
    
    for step in range(10):
        # Take action (continue for all buses)
        actions = [0] * env.num_buses
        
        # Step environment
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        print(f"\nStep {step + 1}:")
        print(f"  Reward: {reward:.2f}")
        print(f"  Done: {done}, Truncated: {truncated}")
        
        # Check bus states
        for bus in env.bus_fleet.buses:
            if bus.load > 0:
                print(f"    Bus {bus.id}: {bus.load} passengers at ({bus.x:.1f}, {bus.y:.1f})")
        
        # Check stop states
        for stop in env.city_grid.stops:
            if stop.queue_len > 0:
                print(f"    Stop {stop.id}: {stop.queue_len} passengers waiting")
        
        if done or truncated:
            print(f"Episode ended at step {step + 1}")
            break
    
    # Final state
    print(f"\nFinal state:")
    for bus in env.bus_fleet.buses:
        print(f"  Bus {bus.id}: {bus.load} passengers at ({bus.x:.1f}, {bus.y:.1f})")
    
    for stop in env.city_grid.stops:
        if stop.queue_len > 0:
            print(f"  Stop {stop.id}: {stop.queue_len} passengers waiting")
    
    return True

if __name__ == "__main__":
    debug_simple()
