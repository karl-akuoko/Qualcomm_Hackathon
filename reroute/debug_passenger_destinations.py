#!/usr/bin/env python3
"""
Debug passenger destinations and bus routing
"""

import os
import sys
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def debug_passenger_destinations():
    """Debug passenger destinations and bus routing"""
    
    print("🔍 DEBUGGING PASSENGER DESTINATIONS AND BUS ROUTING")
    print("=" * 60)
    
    # Create environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=20,  # Reduced for better balance
        num_buses=8,   # Increased for better coverage
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
    
    # Track passenger destinations and bus routes
    passenger_destinations = {}
    bus_routes = {}
    
    print(f"\nRunning simulation for 15 steps...")
    
    for step in range(15):
        # Generate new riders
        new_riders = env.rider_generator.generate_arrivals(env.current_time, env.time_step)
        env.rider_queue.add_riders(new_riders)
        
        # Track passenger destinations
        for rider in new_riders:
            if rider.origin not in passenger_destinations:
                passenger_destinations[rider.origin] = []
            passenger_destinations[rider.origin].append(rider.destination)
        
        # Track bus routes
        for bus_id, bus in env.bus_fleet.buses.items():
            if bus.route:
                bus_routes[bus_id] = bus.route[:5]  # First 5 stops in route
        
        # Get current metrics
        total_waiting = sum(env.rider_queue.get_queue_length(stop_id) for stop_id in env.city_grid.stops.keys())
        total_bus_load = sum(bus.load for bus in env.bus_fleet.buses.values())
        
        print(f"\nStep {step + 1}:")
        print(f"  New riders: {len(new_riders)}")
        print(f"  Total waiting: {total_waiting}")
        print(f"  Total bus load: {total_bus_load}")
        
        # Show passenger destinations
        if new_riders:
            print(f"  Sample destinations: {[r.destination for r in new_riders[:5]]}")
        
        # Show bus states
        for bus_id, bus in env.bus_fleet.buses.items():
            if bus.load > 0:
                print(f"    Bus {bus_id}: {bus.load} passengers at stop {bus.current_node}")
                if bus.route:
                    print(f"      Route: {bus.route[:3]}...")
        
        # Take action (continue for all buses)
        actions = [0] * env.num_buses
        
        # Step environment
        obs, reward, done, truncated, info = env.step(np.array(actions))
        
        if done or truncated:
            print(f"Episode ended at step {step + 1}")
            break
    
    # Analyze passenger destinations
    print(f"\n📊 PASSENGER DESTINATION ANALYSIS:")
    for origin, destinations in passenger_destinations.items():
        if destinations:
            print(f"  Stop {origin}: {len(destinations)} passengers → {set(destinations)}")
    
    # Analyze bus routes
    print(f"\n🚌 BUS ROUTE ANALYSIS:")
    for bus_id, route in bus_routes.items():
        if route:
            print(f"  Bus {bus_id}: {route}")
    
    # Check if buses are visiting passenger destinations
    print(f"\n🎯 DESTINATION COVERAGE ANALYSIS:")
    all_destinations = set()
    for destinations in passenger_destinations.values():
        all_destinations.update(destinations)
    
    all_bus_stops = set()
    for route in bus_routes.values():
        all_bus_stops.update(route)
    
    destinations_covered = all_destinations.intersection(all_bus_stops)
    destinations_missed = all_destinations - all_bus_stops
    
    print(f"  Total passenger destinations: {len(all_destinations)}")
    print(f"  Destinations covered by bus routes: {len(destinations_covered)}")
    print(f"  Destinations missed: {len(destinations_missed)}")
    
    if destinations_missed:
        print(f"  Missed destinations: {list(destinations_missed)[:10]}")
    
    # Check if buses are actually moving
    print(f"\n🚌 BUS MOVEMENT ANALYSIS:")
    for bus_id, bus in env.bus_fleet.buses.items():
        print(f"  Bus {bus_id}:")
        print(f"    Current: {bus.current_node}")
        print(f"    Target: {bus.target_node}")
        print(f"    Moving: {bus.is_moving}")
        print(f"    Load: {bus.load}")
        print(f"    Route: {bus.route[:3] if bus.route else 'None'}")
    
    # Check passenger drop-off logic
    print(f"\n🚌 PASSENGER DROP-OFF ANALYSIS:")
    total_passengers_served = 0
    for bus in env.bus_fleet.buses.values():
        # Count passengers that should have been dropped off
        for passenger in bus.passengers:
            if passenger.destination == bus.current_node:
                total_passengers_served += 1
    
    print(f"  Passengers ready to be dropped off: {total_passengers_served}")
    
    # Check if buses are at passenger destinations
    print(f"\n🎯 BUS-PASSENGER DESTINATION MATCHING:")
    for bus_id, bus in env.bus_fleet.buses.items():
        if bus.load > 0:
            passenger_dests = [p.destination for p in bus.passengers]
            current_stop = bus.current_node
            matches = [dest for dest in passenger_dests if dest == current_stop]
            print(f"  Bus {bus_id} at stop {current_stop}: {len(matches)}/{len(passenger_dests)} passengers can be dropped off")
            if matches:
                print(f"    Passenger destinations: {passenger_dests}")
                print(f"    Current stop: {current_stop}")
                print(f"    Matches: {matches}")

if __name__ == "__main__":
    debug_passenger_destinations()
