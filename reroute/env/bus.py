"""
Bus entity for the routing simulation.
Handles bus movement, passenger loading, and route management.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class BusAction(Enum):
    """Available actions for a bus."""
    CONTINUE = 0
    GO_TO_HIGH_DEMAND = 1
    SKIP_LOW_DEMAND = 2
    SHORT_HOLD = 3


@dataclass
class Bus:
    """Bus with position, capacity, and route information."""
    id: int
    x: float
    y: float
    load: int = 0
    capacity: int = 50
    next_stop: Optional[int] = None
    route: List[int] = None
    mode: str = "static"  # "static" or "rl"
    target_pos: Optional[Tuple[float, float]] = None
    path: List[Tuple[int, int]] = None
    path_index: int = 0
    last_action: BusAction = BusAction.CONTINUE
    replan_count: int = 0
    fuel_km: float = 0.0
    
    def __post_init__(self):
        if self.route is None:
            self.route = []
        if self.path is None:
            self.path = []
    
    def update_position(self, city, dt: float = 1.0):
        """Update bus position along current path."""
        if not self.path or self.path_index >= len(self.path):
            return
        
        current_target = self.path[self.path_index]
        
        # Calculate distance to target
        dx = current_target[0] - self.x
        dy = current_target[1] - self.y
        distance = np.sqrt(dx*dx + dy*dy)
        
        if distance < 0.1:  # Close enough to target
            self.x, self.y = current_target
            self.path_index += 1
            
            # Update fuel consumption
            if self.path_index > 0:
                prev_pos = self.path[self.path_index - 1]
                step_distance = np.sqrt((current_target[0] - prev_pos[0])**2 + 
                                      (current_target[1] - prev_pos[1])**2)
                self.fuel_km += step_distance * 0.001  # Convert to km
        else:
            # Move towards target
            speed = 1.0  # grid units per second
            move_distance = speed * dt
            
            if move_distance >= distance:
                self.x, self.y = current_target
                self.path_index += 1
            else:
                # Move partway
                self.x += (dx / distance) * move_distance
                self.y += (dy / distance) * move_distance
    
    def is_at_stop(self, stop_pos: Tuple[int, int], tolerance: float = 0.5) -> bool:
        """Check if bus is at a stop."""
        dx = self.x - stop_pos[0]
        dy = self.y - stop_pos[1]
        return np.sqrt(dx*dx + dy*dy) < tolerance
    
    def load_passengers(self, city, max_load: int = None) -> int:
        """Load passengers from current stop."""
        if max_load is None:
            max_load = self.capacity - self.load
        
        # Find current stop
        current_stop = None
        for stop in city.stops.values():
            if self.is_at_stop((stop.x, stop.y)):
                current_stop = stop
                break
        
        if current_stop is None:
            return 0
        
        # Load passengers
        available_space = min(max_load, self.capacity - self.load)
        passengers_loaded = min(available_space, current_stop.queue_len)
        
        self.load += passengers_loaded
        current_stop.queue_len -= passengers_loaded
        
        return passengers_loaded
    
    def unload_passengers(self, city, stop_id: int) -> int:
        """Unload passengers at a specific stop."""
        # For simplicity, assume all passengers get off at their destination
        # In a more complex model, we'd track individual passenger destinations
        passengers_unloaded = self.load
        self.load = 0
        return passengers_unloaded
    
    def set_route(self, city, route_stops: List[int]):
        """Set bus route and calculate path."""
        self.route = route_stops
        self.path = []
        
        if not route_stops:
            return
        
        # Calculate path through all stops
        current_pos = (int(self.x), int(self.y))
        
        for stop_id in route_stops:
            stop = city.stops[stop_id]
            stop_pos = (stop.x, stop.y)
            
            # Get path from current position to stop
            path_segment = city.get_shortest_path(current_pos, stop_pos)
            
            # Add to total path (avoid duplicating current position)
            if self.path:
                self.path.extend(path_segment[1:])
            else:
                self.path.extend(path_segment)
            
            current_pos = stop_pos
        
        self.path_index = 0
    
    def replan_route(self, city, target_stops: List[int]):
        """Replan route to target stops."""
        if target_stops != self.route:
            self.set_route(city, target_stops)
            self.replan_count += 1
    
    def get_next_stop_id(self) -> Optional[int]:
        """Get the next stop ID the bus is heading to."""
        if not self.route or not self.path:
            return None
        
        # Find which stop we're closest to on our path
        for stop_id in self.route:
            stop = None
            # Find stop in city (need city reference)
            # For now, return None
            pass
        
        return None
    
    def get_eta_to_stop(self, city, stop_id: int) -> float:
        """Calculate ETA to a specific stop."""
        stop = city.stops[stop_id]
        stop_pos = (stop.x, stop.y)
        
        # Calculate remaining path to stop
        current_pos = (int(self.x), int(self.y))
        
        # Find stop in current path
        if stop_pos in self.path:
            stop_index = self.path.index(stop_pos)
            remaining_path = self.path[stop_index:]
        else:
            # Stop not in current path, calculate direct path
            remaining_path = city.get_shortest_path(current_pos, stop_pos)
        
        # Calculate travel time
        total_time = 0.0
        for i in range(len(remaining_path) - 1):
            travel_time = city.get_travel_time(remaining_path[i], remaining_path[i + 1])
            if travel_time == float('inf'):
                return float('inf')
            total_time += travel_time
        
        return total_time
    
    def get_state_vector(self, city) -> np.ndarray:
        """Get bus state as vector for RL agent."""
        # Basic state: position, load, capacity, next stop info
        state = np.array([
            self.x / city.grid_size,  # Normalized position
            self.y / city.grid_size,
            self.load / self.capacity,  # Load ratio
            len(self.path) / 100.0 if self.path else 0.0,  # Path length
            self.path_index / len(self.path) if self.path else 0.0,  # Progress
        ])
        
        # Add next stop queue length if available
        if self.route:
            next_stop_id = self.route[0] if self.route else None
            if next_stop_id is not None:
                next_stop = city.stops[next_stop_id]
                state = np.append(state, next_stop.queue_len / 20.0)  # Normalized queue
            else:
                state = np.append(state, 0.0)
        else:
            state = np.append(state, 0.0)
        
        return state.astype(np.float32)
