import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from riders import Rider

class BusMode(Enum):
    STATIC = "static"
    RL = "rl"

class BusAction(Enum):
    CONTINUE = 0      # Continue on current route
    HIGH_DEMAND = 1   # Go to highest demand stop
    SKIP_LOW = 2      # Skip next low-demand stop
    SHORT_HOLD = 3    # Hold at current stop briefly

@dataclass
class Bus:
    id: int
    x: int
    y: int
    current_node: int
    load: int = 0
    capacity: int = 40
    next_stop: Optional[int] = None
    route: List[int] = field(default_factory=list)
    mode: BusMode = BusMode.STATIC
    passengers: List[Rider] = field(default_factory=list)
    
    # Movement state
    target_node: Optional[int] = None
    path: List[int] = field(default_factory=list)
    path_index: int = 0
    travel_progress: float = 0.0  # Progress along current edge (0-1)
    
    # Statistics
    total_distance: float = 0.0
    replan_count: int = 0
    hold_time_remaining: float = 0.0
    
    @property
    def available_capacity(self) -> int:
        return self.capacity - self.load
    
    @property
    def is_full(self) -> bool:
        return self.load >= self.capacity
    
    @property
    def is_moving(self) -> bool:
        return self.target_node is not None
    
    @property
    def utilization(self) -> float:
        return self.load / self.capacity

class BusFleet:
    """Manages a fleet of buses"""
    
    def __init__(self, city_grid, num_buses: int = 6):
        self.city_grid = city_grid
        self.buses: Dict[int, Bus] = {}
        self.num_buses = num_buses
        
        # Static routes (baseline) - create this first
        self.static_routes = self._generate_static_routes()
        
        # Initialize buses
        self._initialize_buses()
    
    def _initialize_buses(self):
        """Initialize buses at strategic locations"""
        stop_ids = list(self.city_grid.stops.keys())
        
        for i in range(self.num_buses):
            # Distribute buses across different stops
            start_stop = stop_ids[i % len(stop_ids)]
            stop = self.city_grid.stops[start_stop]
            
            bus = Bus(
                id=i,
                x=stop.x,
                y=stop.y,
                current_node=start_stop,
                route=self.static_routes[i % len(self.static_routes)].copy()
            )
            
            # Set initial target as first stop in route
            if bus.route:
                bus.next_stop = bus.route[0]
            
            self.buses[i] = bus
    
    def _generate_static_routes(self) -> List[List[int]]:
        """Generate fixed circular routes for baseline comparison"""
        stop_ids = list(self.city_grid.stops.keys())
        routes = []
        
        # Create overlapping circular routes to ensure coverage
        stops_per_route = max(4, len(stop_ids) // 3)
        
        for i in range(3):  # 3 main routes
            start_idx = i * (stops_per_route // 2)
            route_stops = []
            
            for j in range(stops_per_route):
                stop_idx = (start_idx + j) % len(stop_ids)
                route_stops.append(stop_ids[stop_idx])
            
            # Make it circular
            route_stops.append(route_stops[0])
            routes.append(route_stops)
        
        return routes
    
    def set_mode(self, mode: BusMode):
        """Set operation mode for all buses"""
        for bus in self.buses.values():
            bus.mode = mode
            
            if mode == BusMode.STATIC:
                # Reset to static routes
                bus.route = self.static_routes[bus.id % len(self.static_routes)].copy()
                if bus.route and not bus.is_moving:
                    bus.next_stop = self._get_next_stop_in_route(bus)
    
    def _get_next_stop_in_route(self, bus: Bus) -> Optional[int]:
        """Get next stop in bus's static route"""
        if not bus.route:
            return None
        
        try:
            current_idx = bus.route.index(bus.current_node)
            next_idx = (current_idx + 1) % len(bus.route)
            return bus.route[next_idx]
        except ValueError:
            # Bus not in route, go to first stop
            return bus.route[0]
    
    def apply_rl_actions(self, actions: List[int], rider_queue, current_time: float):
        """Apply RL actions to buses"""
        for bus_id, action_int in enumerate(actions):
            if bus_id not in self.buses:
                continue
                
            bus = self.buses[bus_id]
            if bus.mode != BusMode.RL:
                continue
            
            action = BusAction(action_int)
            self._execute_action(bus, action, rider_queue, current_time)
    
    def _execute_action(self, bus: Bus, action: BusAction, rider_queue, current_time: float):
        """Execute a specific action for a bus"""
        if bus.is_moving:
            return  # Can't change action while moving
        
        if action == BusAction.CONTINUE:
            # Continue current behavior
            if bus.next_stop is None:
                bus.next_stop = self._find_nearest_stop(bus)
        
        elif action == BusAction.HIGH_DEMAND:
            # Go to highest demand stop
            high_demand_stop = self._find_highest_demand_stop(bus, rider_queue)
            if high_demand_stop and high_demand_stop != bus.current_node:
                bus.next_stop = high_demand_stop
                bus.replan_count += 1
        
        elif action == BusAction.SKIP_LOW:
            # Skip low demand stops
            if bus.next_stop:
                queue_len = rider_queue.get_queue_length(bus.next_stop)
                if queue_len < 2:  # Low demand threshold
                    # Find next stop with higher demand
                    alternative = self._find_alternative_stop(bus, rider_queue)
                    if alternative:
                        bus.next_stop = alternative
                        bus.replan_count += 1
        
        elif action == BusAction.SHORT_HOLD:
            # Hold at current stop for better spacing
            bus.hold_time_remaining = 2.0  # Hold for 2 minutes
    
    def _find_highest_demand_stop(self, bus: Bus, rider_queue) -> Optional[int]:
        """Find stop with highest rider demand"""
        max_demand = 0
        best_stop = None
        
        for stop_id in self.city_grid.stops.keys():
            if stop_id == bus.current_node:
                continue
            
            queue_len = rider_queue.get_queue_length(stop_id)
            # Weight by inverse distance
            distance = self.city_grid.distance_between_stops(bus.current_node, stop_id)
            if distance > 0:
                weighted_demand = queue_len / (1 + distance / 10)  # Normalize distance
                if weighted_demand > max_demand:
                    max_demand = weighted_demand
                    best_stop = stop_id
        
        return best_stop
    
    def _find_alternative_stop(self, bus: Bus, rider_queue) -> Optional[int]:
        """Find alternative stop with higher demand"""
        if not bus.next_stop:
            return None
        
        current_demand = rider_queue.get_queue_length(bus.next_stop)
        
        # Look for nearby stops with higher demand
        for stop_id in self.city_grid.stops.keys():
            if stop_id in [bus.current_node, bus.next_stop]:
                continue
            
            queue_len = rider_queue.get_queue_length(stop_id)
            if queue_len > current_demand + 1:  # Significantly higher demand
                distance = self.city_grid.distance_between_stops(bus.current_node, stop_id)
                if distance <= 8:  # Within reasonable distance
                    return stop_id
        
        return None
    
    def _find_nearest_stop(self, bus: Bus) -> Optional[int]:
        """Find nearest stop to bus"""
        min_distance = float('inf')
        nearest_stop = None
        
        for stop_id in self.city_grid.stops.keys():
            if stop_id == bus.current_node:
                continue
            
            distance = self.city_grid.distance_between_stops(bus.current_node, stop_id)
            if distance < min_distance:
                min_distance = distance
                nearest_stop = stop_id
        
        return nearest_stop
    
    def update_movement(self, time_step: float):
        """Update bus positions and movement"""
        for bus in self.buses.values():
            # Handle holding
            if bus.hold_time_remaining > 0:
                bus.hold_time_remaining = max(0, bus.hold_time_remaining - time_step)
                continue
            
            # Start new movement if needed
            if not bus.is_moving and bus.next_stop:
                self._start_movement_to_stop(bus)
            
            # Update current movement
            if bus.is_moving:
                self._update_bus_movement(bus, time_step)
    
    def _start_movement_to_stop(self, bus: Bus):
        """Start bus movement to target stop"""
        if not bus.next_stop:
            return
        
        # Find path to target stop
        path = self.city_grid.shortest_path(bus.current_node, bus.next_stop)
        
        if len(path) > 1:
            bus.path = path
            bus.path_index = 0
            bus.target_node = path[1]  # Next node in path
            bus.travel_progress = 0.0
    
    def _update_bus_movement(self, bus: Bus, time_step: float):
        """Update bus position along its path"""
        if not bus.path or bus.path_index >= len(bus.path) - 1:
            bus.target_node = None
            return
        
        current_node = bus.path[bus.path_index]
        next_node = bus.path[bus.path_index + 1]
        
        # Get travel time for this edge
        travel_time = self.city_grid.get_travel_time(current_node, next_node)
        if travel_time == float('inf'):
            # Road is closed, replan
            self._replan_route(bus)
            return
        
        # Update progress
        progress_per_minute = 1.0 / travel_time  # Complete edge in travel_time minutes
        bus.travel_progress += progress_per_minute * time_step
        bus.total_distance += time_step * 0.1  # Rough distance tracking
        
        # Check if reached next node
        if bus.travel_progress >= 1.0:
            bus.travel_progress = 0.0
            bus.path_index += 1
            bus.current_node = next_node
            
            # Update bus position
            if next_node in self.city_grid.stops:
                stop = self.city_grid.stops[next_node]
                bus.x = stop.x
                bus.y = stop.y
            
            # Check if reached destination
            if bus.path_index >= len(bus.path) - 1:
                bus.target_node = None
                bus.path = []
                bus.path_index = 0
                
                # Arrived at stop, set up next destination
                if bus.mode == BusMode.STATIC:
                    bus.next_stop = self._get_next_stop_in_route(bus)
                else:
                    bus.next_stop = None  # RL will decide next
            else:
                bus.target_node = bus.path[bus.path_index + 1]
    
    def _replan_route(self, bus: Bus):
        """Replan route when path is blocked"""
        if not bus.next_stop:
            return
        
        new_path = self.city_grid.shortest_path(bus.current_node, bus.next_stop)
        if len(new_path) > 1:
            bus.path = new_path
            bus.path_index = 0
            bus.target_node = new_path[1]
            bus.travel_progress = 0.0
            bus.replan_count += 1
        else:
            # No path available, stay put
            bus.target_node = None
            bus.next_stop = None
    
    def process_stop_arrivals(self, rider_queue, current_time: float):
        """Handle bus arrivals at stops (pickup/dropoff)"""
        for bus in self.buses.values():
            # Only process if bus is at a stop and not moving
            if bus.is_moving or bus.current_node not in self.city_grid.stops:
                continue
            
            # Drop off passengers
            passengers_dropped = []
            for passenger in bus.passengers[:]:
                if passenger.destination == bus.current_node:
                    bus.passengers.remove(passenger)
                    bus.load -= 1
                    passengers_dropped.append(passenger)
            
            # Pick up new passengers
            if bus.available_capacity > 0:
                new_passengers = rider_queue.pick_up_riders(
                    bus.current_node, 
                    bus.available_capacity, 
                    current_time
                )
                bus.passengers.extend(new_passengers)
                bus.load += len(new_passengers)
    
    def get_state_vector(self, rider_queue) -> np.ndarray:
        """Get state representation for RL"""
        state = []
        
        for bus in self.buses.values():
            # Bus features
            state.extend([
                bus.x / 20.0,  # Normalized position
                bus.y / 20.0,
                bus.load / bus.capacity,  # Utilization
                1.0 if bus.is_moving else 0.0,
                bus.hold_time_remaining / 5.0  # Normalized hold time
            ])
        
        # Stop features
        for stop_id in sorted(self.city_grid.stops.keys()):
            queue_len = rider_queue.get_queue_length(stop_id)
            state.append(min(queue_len / 10.0, 1.0))  # Normalized queue length
        
        return np.array(state, dtype=np.float32)
    
    def get_fleet_stats(self) -> Dict[str, float]:
        """Get fleet-wide statistics"""
        total_load = sum(bus.load for bus in self.buses.values())
        total_capacity = sum(bus.capacity for bus in self.buses.values())
        total_distance = sum(bus.total_distance for bus in self.buses.values())
        total_replans = sum(bus.replan_count for bus in self.buses.values())
        
        # Calculate load standard deviation for overcrowding metric
        loads = [bus.load for bus in self.buses.values()]
        load_std = np.std(loads) if len(loads) > 1 else 0.0
        
        return {
            "total_load": total_load,
            "avg_utilization": total_load / total_capacity if total_capacity > 0 else 0.0,
            "load_std": load_std,
            "total_distance": total_distance,
            "total_replans": total_replans,
            "avg_replans": total_replans / len(self.buses) if self.buses else 0.0
        }
    
    def reset_stats(self):
        """Reset all bus statistics"""
        for bus in self.buses.values():
            bus.total_distance = 0.0
            bus.replan_count = 0.0