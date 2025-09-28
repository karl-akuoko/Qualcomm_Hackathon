#!/usr/bin/env python3
"""
Debug Passenger Drop-off in Manhattan System
Check if passengers are actually getting off buses at their destinations
"""

import sys
import os
import json
import time

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__)))

from manhattan_data_parser import ManhattanDataParser, ManhattanStop, ManhattanRoute

class ManhattanBusDispatchSystem:
    """Manhattan bus dispatch system for debugging"""
    
    def __init__(self):
        self.parser = ManhattanDataParser()
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        
        # Load Manhattan data
        self._load_manhattan_data()
        self._initialize_system()
    
    def _load_manhattan_data(self):
        """Load real Manhattan bus data"""
        print("🗽 Loading Manhattan bus data...")
        
        self.stops = self.parser.load_manhattan_stops()
        self.routes = self.parser.create_manhattan_routes()
        
        print(f"✅ Loaded {len(self.stops)} stops and {len(self.routes)} routes")
    
    def _initialize_system(self):
        """Initialize the Manhattan bus system"""
        print("🚌 Initializing Manhattan bus system...")
        
        # Create buses for each route
        self.buses = {}
        bus_id = 0
        
        for route_id, route in self.routes.items():
            # Create 2-3 buses per route
            num_buses = 2 if "SBS" in route_id else 3
            
            for i in range(num_buses):
                bus = {
                    "id": bus_id,
                    "route_id": route_id,
                    "route_name": route.route_name,
                    "current_stop": route.stops[0] if route.stops else None,
                    "next_stop_index": 0,
                    "x": self.stops[route.stops[0]].x if route.stops else 0,
                    "y": self.stops[route.stops[0]].y if route.stops else 0,
                    "load": 0,
                    "capacity": 40,
                    "color": route.color,
                    "direction": route.direction,
                    "speed": 2.0,
                    "status": "moving",
                    "passengers": [],
                    "stuck_counter": 0,
                    "last_position": (self.stops[route.stops[0]].x, self.stops[route.stops[0]].y) if route.stops else (0, 0)
                }
                self.buses[bus_id] = bus
                bus_id += 1
        
        # Initialize passenger queues at stops
        self.passengers = {}
        for stop_id, stop in self.stops.items():
            self.passengers[stop_id] = {
                "waiting": [],
                "total_wait_time": 0.0,
                "queue_length": 0
            }
        
        print(f"✅ Initialized {len(self.buses)} buses on {len(self.routes)} routes")
    
    def get_manhattan_demand(self, stop_id: str, hour: int) -> float:
        """Get realistic demand for Manhattan stops"""
        stop = self.stops[stop_id]
        
        # Base demand by location
        base_demand = 1.0
        
        # Major transfer points have higher demand
        if "TRANS" in stop_id:
            base_demand = 2.5
        elif any(route in stop.routes for route in ["M1", "M2", "M3", "M4"]):  # 5th Ave
            base_demand = 1.8
        elif any(route in stop.routes for route in ["M5", "M7", "M104"]):  # Broadway
            base_demand = 1.6
        elif "M14" in stop.routes[0] if stop.routes else False:  # 14th St
            base_demand = 1.4
        
        # Time-based demand patterns
        if 7 <= hour <= 9:  # Morning rush
            time_factor = 1.5
        elif 17 <= hour <= 19:  # Evening rush
            time_factor = 1.3
        elif 10 <= hour <= 16:  # Midday
            time_factor = 0.8
        else:  # Night
            time_factor = 0.3
        
        return base_demand * time_factor
    
    def generate_passengers(self):
        """Generate passengers based on Manhattan demand patterns"""
        current_hour = (self.simulation_time // 3600) % 24
        
        for stop_id, stop in self.stops.items():
            demand = self.get_manhattan_demand(stop_id, current_hour)
            
            # Generate passengers based on demand
            if random.random() < demand * 0.05:  # Reduced rate
                # Create passenger with destination
                destination_stops = [s for s in self.stops.keys() if s != stop_id]
                destination = random.choice(destination_stops)
                
                passenger = {
                    "id": f"p_{len(self.passengers[stop_id]['waiting'])}",
                    "destination": destination,
                    "arrival_time": self.simulation_time,
                    "wait_time": 0
                }
                
                self.passengers[stop_id]["waiting"].append(passenger)
                self.passengers[stop_id]["queue_length"] = len(self.passengers[stop_id]["waiting"])
    
    def move_buses(self):
        """Move buses with anti-stuck logic"""
        for bus_id, bus in self.buses.items():
            if bus["status"] != "moving":
                continue
            
            # Check if bus is stuck
            current_pos = (bus["x"], bus["y"])
            if current_pos == bus["last_position"]:
                bus["stuck_counter"] += 1
            else:
                bus["stuck_counter"] = 0
                bus["last_position"] = current_pos
            
            # If stuck for too long, force movement
            if bus["stuck_counter"] > 10:
                self._unstuck_bus(bus_id)
                continue
            
            # Normal movement logic
            route = self.routes[bus["route_id"]]
            
            if bus["next_stop_index"] >= len(route.stops):
                bus["next_stop_index"] = 0
            
            next_stop_id = route.stops[bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # Move towards next stop
            dx = next_stop.x - bus["x"]
            dy = next_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 3:  # Arrived at stop
                self._process_bus_arrival(bus_id, next_stop_id)
                bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
                bus["current_stop"] = next_stop_id
            else:
                # Move towards next stop with minimum movement
                move_x = int(dx / max(1, distance) * bus["speed"])
                move_y = int(dy / max(1, distance) * bus["speed"])
                
                # Ensure minimum movement
                if abs(move_x) < 1 and dx != 0:
                    move_x = 1 if dx > 0 else -1
                if abs(move_y) < 1 and dy != 0:
                    move_y = 1 if dy > 0 else -1
                
                bus["x"] += move_x
                bus["y"] += move_y
    
    def _unstuck_bus(self, bus_id: int):
        """Force unstuck a bus"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        # Move to next stop directly
        next_stop_id = route.stops[bus["next_stop_index"]]
        next_stop = self.stops[next_stop_id]
        
        bus["x"] = next_stop.x
        bus["y"] = next_stop.y
        bus["stuck_counter"] = 0
        bus["last_position"] = (next_stop.x, next_stop.y)
        
        # Process arrival
        self._process_bus_arrival(bus_id, next_stop_id)
        bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
        bus["current_stop"] = next_stop_id
    
    def _process_bus_arrival(self, bus_id: int, stop_id: str):
        """Process bus arrival at stop - THIS IS WHERE DROP-OFF SHOULD HAPPEN"""
        bus = self.buses[bus_id]
        stop_passengers = self.passengers[stop_id]
        
        print(f"🚌 Bus {bus_id} arrived at stop {stop_id}")
        print(f"   Bus load before: {bus['load']}")
        print(f"   Passengers on bus: {len(bus.get('passengers', []))}")
        
        # DROP OFF PASSENGERS - This is the critical part!
        passengers_to_drop = []
        for passenger in bus.get("passengers", []):
            if passenger["destination"] == stop_id:
                passengers_to_drop.append(passenger)
                print(f"   ✅ Passenger {passenger['id']} getting off at destination {stop_id}")
        
        # Remove dropped passengers from bus
        for passenger in passengers_to_drop:
            bus["passengers"].remove(passenger)
            bus["load"] -= 1
        
        print(f"   Bus load after drop-off: {bus['load']}")
        print(f"   Passengers dropped off: {len(passengers_to_drop)}")
        
        # Pick up passengers
        passengers_to_pickup = []
        pickup_limit = min(5, bus["capacity"] - bus["load"])  # Limit pickup rate
        
        for i, passenger in enumerate(stop_passengers["waiting"][:pickup_limit]):
            if bus["load"] < bus["capacity"]:
                passengers_to_pickup.append(passenger)
                stop_passengers["waiting"].remove(passenger)
                bus["load"] += 1
                print(f"   ✅ Passenger {passenger['id']} getting on bus")
        
        # Add picked up passengers to bus
        if not bus.get("passengers"):
            bus["passengers"] = []
        bus["passengers"].extend(passengers_to_pickup)
        
        print(f"   Bus load after pickup: {bus['load']}")
        print(f"   Passengers picked up: {len(passengers_to_pickup)}")
        
        # Update stop queue
        stop_passengers["queue_length"] = len(stop_passengers["waiting"])
        
        print(f"   Stop {stop_id} queue length: {stop_passengers['queue_length']}")
        print("   " + "="*50)
    
    def update_wait_times(self):
        """Update passenger wait times"""
        for stop_id, stop_passengers in self.passengers.items():
            for passenger in stop_passengers["waiting"]:
                passenger["wait_time"] += 1
            
            # Update total wait time
            stop_passengers["total_wait_time"] = sum(p["wait_time"] for p in stop_passengers["waiting"])
    
    def step(self):
        """Perform one simulation step"""
        self.simulation_time += 1
        
        # Generate new passengers
        self.generate_passengers()
        
        # Move buses
        self.move_buses()
        
        # Update wait times
        self.update_wait_times()
    
    def get_system_state(self):
        """Get current system state"""
        total_wait_time = sum(stop["total_wait_time"] for stop in self.passengers.values())
        total_passengers = sum(len(stop["waiting"]) for stop in self.passengers.values())
        avg_wait_time = total_wait_time / max(1, total_passengers)
        
        # Count passengers on buses
        total_passengers_on_buses = sum(len(bus.get("passengers", [])) for bus in self.buses.values())
        
        return {
            "simulation_time": self.simulation_time,
            "total_passengers_waiting": total_passengers,
            "total_passengers_on_buses": total_passengers_on_buses,
            "avg_wait_time": avg_wait_time,
            "buses": [
                {
                    "id": bus["id"],
                    "load": bus["load"],
                    "passengers": len(bus.get("passengers", [])),
                    "current_stop": bus["current_stop"]
                }
                for bus in self.buses.values()
            ],
            "stops": [
                {
                    "id": stop_id,
                    "queue_length": self.passengers[stop_id]["queue_length"],
                    "total_wait_time": self.passengers[stop_id]["total_wait_time"]
                }
                for stop_id, stop in self.stops.items()
            ]
        }

def main():
    """Debug passenger drop-off"""
    print("🔍 DEBUGGING PASSENGER DROP-OFF")
    print("=" * 50)
    
    # Create system
    system = ManhattanBusDispatchSystem()
    
    # Run simulation for a few steps
    print("\n🚌 Running simulation for 20 steps...")
    for step in range(20):
        print(f"\n--- Step {step + 1} ---")
        system.step()
        
        # Get system state
        state = system.get_system_state()
        print(f"Simulation time: {state['simulation_time']}")
        print(f"Passengers waiting: {state['total_passengers_waiting']}")
        print(f"Passengers on buses: {state['total_passengers_on_buses']}")
        print(f"Average wait time: {state['avg_wait_time']:.2f}")
        
        # Show bus details
        print("\nBus details:")
        for bus in state['buses'][:5]:  # Show first 5 buses
            print(f"  Bus {bus['id']}: load={bus['load']}, passengers={bus['passengers']}, stop={bus['current_stop']}")
        
        time.sleep(0.5)  # Slow down for observation
    
    print("\n✅ Debug complete!")

if __name__ == "__main__":
    import random
    main()
