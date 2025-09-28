#!/usr/bin/env python3
"""
Diagnose the bus dispatch system to understand wait time issues
"""

import os
import sys
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def diagnose_system():
    """Diagnose the system to understand wait time issues"""
    
    print("🔍 DIAGNOSING BUS DISPATCH SYSTEM")
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
    
    print(f"System Configuration:")
    print(f"  Grid: 20x20")
    print(f"  Stops: {len(env.city_grid.stops)}")
    print(f"  Buses: {len(env.bus_fleet.buses)}")
    print(f"  Bus Capacity: {env.bus_fleet.buses[0].capacity}")
    
    # Check initial state
    print(f"\nInitial State:")
    print(f"  Total waiting passengers: {sum(env.rider_queue.get_queue_length(stop_id) for stop_id in env.city_grid.stops.keys())}")
    print(f"  Total bus load: {sum(bus.load for bus in env.bus_fleet.buses.values())}")
    
    # Run simulation and track metrics
    total_passengers_generated = 0
    total_passengers_served = 0
    wait_times = []
    
    print(f"\nRunning simulation for 20 steps...")
    
    for step in range(20):
        # Generate new riders
        new_riders = env.rider_generator.generate_arrivals(env.current_time, env.time_step)
        total_passengers_generated += len(new_riders)
        env.rider_queue.add_riders(new_riders)
        
        # Get current metrics
        total_waiting = sum(env.rider_queue.get_queue_length(stop_id) for stop_id in env.city_grid.stops.keys())
        total_bus_load = sum(bus.load for bus in env.bus_fleet.buses.values())
        
        # Track wait times
        wait_stats = env.rider_queue.get_wait_time_stats()
        wait_times.append(wait_stats['avg'])
        
        print(f"Step {step + 1}:")
        print(f"  New riders: {len(new_riders)}")
        print(f"  Total waiting: {total_waiting}")
        print(f"  Total bus load: {total_bus_load}")
        print(f"  Avg wait time: {wait_stats['avg']:.2f}")
        
        # Show bus states
        for bus_id, bus in env.bus_fleet.buses.items():
            if bus.load > 0:
                print(f"    Bus {bus_id}: {bus.load} passengers at stop {bus.current_node}")
        
        # Take action (continue for all buses)
        actions = [0] * env.num_buses
        
        # Step environment
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        if done or truncated:
            print(f"Episode ended at step {step + 1}")
            break
    
    # Final analysis
    print(f"\n📊 FINAL ANALYSIS:")
    print(f"  Total passengers generated: {total_passengers_generated}")
    print(f"  Total passengers served: {total_passengers_served}")
    print(f"  System efficiency: {total_passengers_served / max(total_passengers_generated, 1) * 100:.1f}%")
    print(f"  Final wait time: {wait_times[-1] if wait_times else 0:.2f}")
    print(f"  Wait time trend: {'Increasing' if len(wait_times) > 1 and wait_times[-1] > wait_times[0] else 'Stable'}")
    
    # Check if buses are actually moving
    print(f"\n🚌 BUS MOVEMENT ANALYSIS:")
    for bus_id, bus in env.bus_fleet.buses.items():
        print(f"  Bus {bus_id}: at stop {bus.current_node} with {bus.load} passengers")
        print(f"    Target: {bus.target_node}, Moving: {bus.is_moving}")
        print(f"    Route: {bus.route[:3]}..." if bus.route else "    Route: []")
    
    # Check passenger destinations
    print(f"\n🎯 PASSENGER DESTINATION ANALYSIS:")
    waiting_riders = env.rider_queue.get_waiting_riders()
    if waiting_riders:
        destinations = [rider.destination for rider in waiting_riders[:10]]  # First 10
        print(f"  Sample destinations: {destinations}")
    
    # Check if system is overloaded
    print(f"\n⚖️ SYSTEM BALANCE ANALYSIS:")
    print(f"  Buses per stop: {len(env.bus_fleet.buses) / len(env.city_grid.stops):.3f}")
    print(f"  Capacity per stop: {env.bus_fleet.buses[0].capacity * len(env.bus_fleet.buses) / len(env.city_grid.stops):.1f}")
    print(f"  Current demand: {total_waiting}")
    
    if total_waiting > len(env.bus_fleet.buses) * env.bus_fleet.buses[0].capacity:
        print("  ⚠️ SYSTEM OVERLOADED: More passengers than total bus capacity!")
    else:
        print("  ✅ System capacity sufficient")
    
    return wait_times

if __name__ == "__main__":
    wait_times = diagnose_system()
    
    print(f"\n🎯 DIAGNOSIS COMPLETE")
    print(f"Wait times: {wait_times}")
    
    if len(wait_times) > 1 and wait_times[-1] > wait_times[0] * 2:
        print("❌ PROBLEM: Wait times are increasing significantly!")
        print("   Possible causes:")
        print("   1. Buses not dropping off passengers")
        print("   2. System overloaded (too many passengers)")
        print("   3. Buses not moving efficiently")
        print("   4. Scale mismatch (6 buses for 32 stops)")
    else:
        print("✅ Wait times are stable")
