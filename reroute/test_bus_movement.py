#!/usr/bin/env python3
"""
Test bus movement in the real data system
"""

import sys
import os
import json
import time

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from fastapi_manhattan_real_data import RealManhattanBusSystem

def test_bus_movement():
    """Test if buses are moving properly"""
    print("🚌 Testing bus movement...")
    
    # Create system
    system = RealManhattanBusSystem()
    
    print(f"✅ System created with {len(system.buses)} buses and {len(system.stops)} stops")
    
    # Show initial bus positions
    print("\n📍 Initial bus positions:")
    for bus_id, bus in system.buses.items():
        print(f"  Bus {bus_id} ({bus['route_id']}): ({bus['x']}, {bus['y']})")
    
    # Run a few steps
    print("\n🚌 Running simulation steps...")
    for step in range(5):
        system.step()
        print(f"\nStep {step + 1}:")
        for bus_id, bus in system.buses.items():
            print(f"  Bus {bus_id} ({bus['route_id']}): ({bus['x']}, {bus['y']}) - Load: {bus['load']}")
    
    # Get system state
    state = system.get_system_state()
    print(f"\n📊 System state:")
    print(f"  Simulation time: {state['simulation_time']}")
    print(f"  Buses: {len(state['buses'])}")
    print(f"  Stops: {len(state['stops'])}")
    print(f"  Total passengers: {state['kpis']['total_passengers']}")
    print(f"  Average wait time: {state['kpis']['avg_wait_time']:.2f}s")

if __name__ == "__main__":
    test_bus_movement()
