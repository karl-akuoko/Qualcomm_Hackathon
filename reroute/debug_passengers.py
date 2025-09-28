#!/usr/bin/env python3
"""
Debug passenger boarding and wait times
"""

import os
import sys
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def debug_passenger_boarding():
    """Debug passenger boarding mechanics"""
    
    print("🔍 DEBUGGING PASSENGER BOARDING MECHANICS")
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
    
    # Reset environment
    obs, info = env.reset()
    
    print(f"Initial state:")
    print(f"  Buses: {len(env.bus_fleet.buses)}")
    print(f"  Stops: {len(env.city.stops)}")
    print(f"  Riders: {len(env.rider_generator.riders)}")
    
    # Track statistics
    total_passengers_served = 0
    total_wait_time = 0
    step_count = 0
    
    print("\n🔍 Running simulation for 20 steps...")
    
    for step in range(20):
        # Get current state
        bus_states = []
        stop_states = []
        
        for bus in env.bus_fleet.buses:
            bus_states.append({
                'id': bus.id,
                'x': bus.x,
                'y': bus.y,
                'load': bus.load,
                'capacity': bus.capacity,
                'next_stop': bus.next_stop,
                'mode': bus.mode
            })
        
        for stop in env.city.stops:
            stop_states.append({
                'id': stop.id,
                'x': stop.x,
                'y': stop.y,
                'queue_len': stop.queue_len,
                'total_wait': stop.total_wait_time
            })
        
        # Calculate total passengers waiting
        total_waiting = sum(stop['queue_len'] for stop in stop_states)
        total_bus_load = sum(bus['load'] for bus in bus_states)
        
        print(f"\nStep {step + 1}:")
        print(f"  Total passengers waiting: {total_waiting}")
        print(f"  Total bus load: {total_bus_load}")
        print(f"  Total passengers served: {total_passengers_served}")
        
        # Show bus states
        for bus in bus_states:
            if bus['load'] > 0:
                print(f"    Bus {bus['id']}: {bus['load']}/{bus['capacity']} passengers at ({bus['x']:.1f}, {bus['y']:.1f})")
        
        # Show stop states
        for stop in stop_states:
            if stop['queue_len'] > 0:
                print(f"    Stop {stop['id']}: {stop['queue_len']} passengers waiting at ({stop['x']:.1f}, {stop['y']:.1f})")
        
        # Take action (continue for all buses)
        actions = [0] * env.num_buses  # CONTINUE action
        
        # Step environment
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        # Track passengers served
        if 'passengers_served' in info:
            total_passengers_served += info['passengers_served']
        
        # Track wait time
        if 'total_wait_time' in info:
            total_wait_time = info['total_wait_time']
        
        step_count += 1
        
        if done or truncated:
            print(f"\nEpisode ended at step {step + 1}")
            break
    
    # Final statistics
    print(f"\n📊 FINAL STATISTICS:")
    print(f"  Total passengers served: {total_passengers_served}")
    print(f"  Total wait time: {total_wait_time:.2f}")
    print(f"  Average wait time: {total_wait_time / max(total_passengers_served, 1):.2f}")
    print(f"  Steps completed: {step_count}")
    
    # Check if buses are actually moving
    print(f"\n🚌 BUS MOVEMENT ANALYSIS:")
    for bus in env.bus_fleet.buses:
        print(f"  Bus {bus.id}: at ({bus.x:.1f}, {bus.y:.1f}) with {bus.load} passengers")
    
    # Check if stops have passengers
    print(f"\n🚏 STOP ANALYSIS:")
    for stop in env.city.stops:
        if stop.queue_len > 0:
            print(f"  Stop {stop.id}: {stop.queue_len} passengers waiting")
    
    return total_passengers_served, total_wait_time

def debug_wait_time_calculation():
    """Debug wait time calculation"""
    
    print("\n🔍 DEBUGGING WAIT TIME CALCULATION")
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
    
    # Reset environment
    obs, info = env.reset()
    
    print("Initial rider generation:")
    print(f"  Total riders: {len(env.rider_generator.riders)}")
    
    # Check rider generation
    for i, rider in enumerate(env.rider_generator.riders[:5]):  # Show first 5 riders
        print(f"  Rider {i}: from stop {rider.origin_stop} to stop {rider.destination_stop}, wait time: {rider.wait_time}")
    
    # Run a few steps
    for step in range(5):
        actions = [0] * env.num_buses
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        print(f"\nStep {step + 1}:")
        print(f"  Reward: {reward:.2f}")
        print(f"  Info: {info}")
        
        if done or truncated:
            break
    
    return True

def main():
    """Main debugging function"""
    
    print("🚌 BUS DISPATCH PASSENGER BOARDING DEBUG")
    print("=" * 60)
    
    # Debug passenger boarding
    passengers_served, wait_time = debug_passenger_boarding()
    
    # Debug wait time calculation
    debug_wait_time_calculation()
    
    print(f"\n✅ DEBUGGING COMPLETE")
    print(f"Passengers served: {passengers_served}")
    print(f"Wait time: {wait_time:.2f}")
    
    if passengers_served == 0:
        print("❌ NO PASSENGERS WERE SERVED - THIS IS THE PROBLEM!")
    else:
        print(f"✅ {passengers_served} passengers were served")

if __name__ == "__main__":
    main()
