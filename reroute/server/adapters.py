"""
Adapters for different dispatch strategies and baseline implementations
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
import sys
sys.path.append('../env')
from bus import BusFleet, BusMode, BusAction
from riders import RiderQueue

class DispatchStrategy(Enum):
    STATIC = "static"
    ROUND_ROBIN = "round_robin"
    DEMAND_BASED = "demand_based"
    SHORTEST_PATH = "shortest_path"

class StaticDispatcher:
    """Static baseline dispatcher - fixed routes and schedules"""
    
    def __init__(self, bus_fleet: BusFleet):
        self.bus_fleet = bus_fleet
        self.strategy = DispatchStrategy.STATIC
        
    def dispatch_actions(self, rider_queue: RiderQueue, current_time: float) -> List[int]:
        """Generate static dispatch actions (all CONTINUE)"""
        return [BusAction.CONTINUE.value] * len(self.bus_fleet.buses)
    
    def get_description(self) -> str:
        return "Fixed schedule with predetermined routes"

class RoundRobinDispatcher:
    """Round-robin dispatcher - cycles through stops"""
    
    def __init__(self, bus_fleet: BusFleet, city_grid):
        self.bus_fleet = bus_fleet
        self.city_grid = city_grid
        self.strategy = DispatchStrategy.ROUND_ROBIN
        self.stop_cycle = list(city_grid.stops.keys())
        self.current_stop_index = 0
        
    def dispatch_actions(self, rider_queue: RiderQueue, current_time: float) -> List[int]:
        """Generate round-robin dispatch actions"""
        actions = []
        
        for bus_id, bus in self.bus_fleet.buses.items():
            if bus.mode != BusMode.RL:
                actions.append(BusAction.CONTINUE.value)
                continue
            
            # Find next stop in cycle
            next_stop = self.stop_cycle[self.current_stop_index % len(self.stop_cycle)]
            self.current_stop_index += 1
            
            # Set bus target
            bus.next_stop = next_stop
            actions.append(BusAction.HIGH_DEMAND.value)
        
        return actions
    
    def get_description(self) -> str:
        return "Round-robin through all stops"

class DemandBasedDispatcher:
    """Demand-based dispatcher - prioritizes high-demand stops"""
    
    def __init__(self, bus_fleet: BusFleet, city_grid):
        self.bus_fleet = bus_fleet
        self.city_grid = city_grid
        self.strategy = DispatchStrategy.DEMAND_BASED
        
    def dispatch_actions(self, rider_queue: RiderQueue, current_time: float) -> List[int]:
        """Generate demand-based dispatch actions"""
        actions = []
        
        # Find high-demand stops
        stop_demands = []
        for stop_id in self.city_grid.stops.keys():
            queue_len = rider_queue.get_queue_length(stop_id)
            stop_demands.append((stop_id, queue_len))
        
        # Sort by demand (descending)
        stop_demands.sort(key=lambda x: x[1], reverse=True)
        high_demand_stops = [stop_id for stop_id, _ in stop_demands[:3]]  # Top 3
        
        for bus_id, bus in self.bus_fleet.buses.items():
            if bus.mode != BusMode.RL:
                actions.append(BusAction.CONTINUE.value)
                continue
            
            # Find nearest high-demand stop
            nearest_high_demand = self._find_nearest_stop(bus, high_demand_stops)
            
            if nearest_high_demand and nearest_high_demand != bus.current_node:
                bus.next_stop = nearest_high_demand
                actions.append(BusAction.HIGH_DEMAND.value)
            else:
                actions.append(BusAction.CONTINUE.value)
        
        return actions
    
    def _find_nearest_stop(self, bus, stop_list: List[int]) -> Optional[int]:
        """Find nearest stop from a list"""
        if not stop_list:
            return None
        
        min_distance = float('inf')
        nearest_stop = None
        
        for stop_id in stop_list:
            if stop_id == bus.current_node:
                continue
            
            distance = self.city_grid.distance_between_stops(bus.current_node, stop_id)
            if distance < min_distance:
                min_distance = distance
                nearest_stop = stop_id
        
        return nearest_stop
    
    def get_description(self) -> str:
        return "Prioritizes stops with highest rider demand"

class ShortestPathDispatcher:
    """Shortest path dispatcher - minimizes travel distance"""
    
    def __init__(self, bus_fleet: BusFleet, city_grid):
        self.bus_fleet = bus_fleet
        self.city_grid = city_grid
        self.strategy = DispatchStrategy.SHORTEST_PATH
        
    def dispatch_actions(self, rider_queue: RiderQueue, current_time: float) -> List[int]:
        """Generate shortest-path dispatch actions"""
        actions = []
        
        for bus_id, bus in self.bus_fleet.buses.items():
            if bus.mode != BusMode.RL:
                actions.append(BusAction.CONTINUE.value)
                continue
            
            # Find nearest stop with riders
            nearest_stop = self._find_nearest_stop_with_riders(bus, rider_queue)
            
            if nearest_stop and nearest_stop != bus.current_node:
                bus.next_stop = nearest_stop
                actions.append(BusAction.HIGH_DEMAND.value)
            else:
                actions.append(BusAction.CONTINUE.value)
        
        return actions
    
    def _find_nearest_stop_with_riders(self, bus, rider_queue: RiderQueue) -> Optional[int]:
        """Find nearest stop that has waiting riders"""
        min_distance = float('inf')
        nearest_stop = None
        
        for stop_id in self.city_grid.stops.keys():
            if stop_id == bus.current_node:
                continue
            
            queue_len = rider_queue.get_queue_length(stop_id)
            if queue_len > 0:  # Only consider stops with riders
                distance = self.city_grid.distance_between_stops(bus.current_node, stop_id)
                if distance < min_distance:
                    min_distance = distance
                    nearest_stop = stop_id
        
        return nearest_stop
    
    def get_description(self) -> str:
        return "Minimizes travel distance to nearest stops with riders"

class DispatcherFactory:
    """Factory for creating different dispatcher types"""
    
    @staticmethod
    def create_dispatcher(dispatcher_type: str, bus_fleet: BusFleet, city_grid=None) -> 'BaseDispatcher':
        """Create dispatcher based on type"""
        
        if dispatcher_type == "static":
            return StaticDispatcher(bus_fleet)
        elif dispatcher_type == "round_robin":
            return RoundRobinDispatcher(bus_fleet, city_grid)
        elif dispatcher_type == "demand_based":
            return DemandBasedDispatcher(bus_fleet, city_grid)
        elif dispatcher_type == "shortest_path":
            return ShortestPathDispatcher(bus_fleet, city_grid)
        else:
            raise ValueError(f"Unknown dispatcher type: {dispatcher_type}")

class BaselineComparison:
    """Compare different baseline strategies"""
    
    def __init__(self, bus_fleet: BusFleet, city_grid):
        self.bus_fleet = bus_fleet
        self.city_grid = city_grid
        self.dispatchers = {}
        self.results = {}
        
        # Initialize all dispatchers
        for strategy in DispatchStrategy:
            try:
                dispatcher = DispatcherFactory.create_dispatcher(
                    strategy.value, bus_fleet, city_grid
                )
                self.dispatchers[strategy.value] = dispatcher
            except Exception as e:
                print(f"Failed to create {strategy.value} dispatcher: {e}")
    
    def run_comparison(self, rider_queue: RiderQueue, current_time: float, 
                      duration: float = 60.0) -> Dict[str, Dict[str, float]]:
        """Run comparison between all dispatchers"""
        
        results = {}
        
        for name, dispatcher in self.dispatchers.items():
            try:
                # Reset bus fleet
                self.bus_fleet.set_mode(BusMode.RL)
                
                # Run dispatcher for duration
                start_time = current_time
                total_reward = 0.0
                total_distance = 0.0
                total_replans = 0.0
                
                while current_time - start_time < duration:
                    actions = dispatcher.dispatch_actions(rider_queue, current_time)
                    
                    # Apply actions (simplified)
                    for i, action in enumerate(actions):
                        if i < len(self.bus_fleet.buses):
                            bus = list(self.bus_fleet.buses.values())[i]
                            if action == BusAction.HIGH_DEMAND.value:
                                bus.replan_count += 1
                    
                    total_distance += sum(bus.total_distance for bus in self.bus_fleet.buses.values())
                    total_replans += sum(bus.replan_count for bus in self.bus_fleet.buses.values())
                    
                    current_time += 0.5  # 30 second steps
                
                # Calculate metrics
                wait_stats = rider_queue.get_wait_time_stats()
                fleet_stats = self.bus_fleet.get_fleet_stats()
                
                results[name] = {
                    'avg_wait': wait_stats['avg'],
                    'p90_wait': wait_stats['p90'],
                    'load_std': fleet_stats['load_std'],
                    'total_distance': total_distance,
                    'total_replans': total_replans,
                    'description': dispatcher.get_description()
                }
                
            except Exception as e:
                print(f"Error running {name} dispatcher: {e}")
                results[name] = {'error': str(e)}
        
        return results
    
    def get_best_dispatcher(self, results: Dict[str, Dict[str, float]], 
                           metric: str = 'avg_wait') -> str:
        """Get best dispatcher based on metric"""
        best_name = None
        best_value = float('inf')
        
        for name, metrics in results.items():
            if 'error' in metrics:
                continue
            
            if metric in metrics:
                value = metrics[metric]
                if value < best_value:
                    best_value = value
                    best_name = name
        
        return best_name
