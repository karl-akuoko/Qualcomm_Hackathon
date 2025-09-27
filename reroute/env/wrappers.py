"""
Gym environment wrapper for the bus routing simulation.
Implements the OpenAI Gym interface for RL training.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import random

from .city import CityGrid
from .bus import Bus, BusAction
from .riders import RiderDemand
from .traffic import TrafficManager
from .reward import RewardCalculator


class BusRoutingEnv(gym.Env):
    """
    Gym environment for bus routing optimization.
    
    Action Space: Discrete actions per bus
    - 0: CONTINUE (follow current route)
    - 1: GO_TO_HIGH_DEMAND (redirect to high-demand stop)
    - 2: SKIP_LOW_DEMAND (skip current stop if low demand)
    - 3: SHORT_HOLD (hold at current stop briefly)
    
    Observation Space: Vector of bus states and city state
    """
    
    def __init__(self, 
                 grid_size: int = 20,
                 num_buses: int = 6,
                 num_stops: int = 35,
                 bus_capacity: int = 50,
                 seed: int = 42):
        
        super().__init__()
        
        # Environment parameters
        self.grid_size = grid_size
        self.num_buses = num_buses
        self.num_stops = num_stops
        self.bus_capacity = bus_capacity
        self.seed = seed
        
        # Set random seeds
        random.seed(seed)
        np.random.seed(seed)
        
        # Initialize components
        self.city = CityGrid(grid_size, num_stops, seed)
        self.buses = self._initialize_buses()
        self.riders = RiderDemand(self.city, seed)
        self.traffic_manager = TrafficManager(self.city)
        self.reward_calculator = RewardCalculator()
        
        # Environment state
        self.current_time = 0.0
        self.dt = 1.0  # Time step in seconds
        self.previous_state = None
        
        # Define action and observation spaces
        self.action_space = spaces.MultiDiscrete([4] * num_buses)  # 4 actions per bus
        self.observation_space = self._get_observation_space()
        
        # Baseline policy for comparison
        self.baseline_mode = False
        self.baseline_metrics = {}
        
        # Episode tracking
        self.episode_length = 0
        self.max_episode_length = 3600  # 1 hour in seconds
        
    def _initialize_buses(self) -> List[Bus]:
        """Initialize buses with random positions and routes."""
        buses = []
        
        for i in range(self.num_buses):
            # Random starting position
            start_x = random.randint(0, self.grid_size - 1)
            start_y = random.randint(0, self.grid_size - 1)
            
            bus = Bus(
                id=i,
                x=float(start_x),
                y=float(start_y),
                capacity=self.bus_capacity
            )
            
            # Create a simple loop route through several stops
            route = self._create_baseline_route(i)
            bus.set_route(self.city, route)
            
            buses.append(bus)
        
        return buses
    
    def _create_baseline_route(self, bus_id: int) -> List[int]:
        """Create a baseline loop route for a bus."""
        # Create different routes for different buses
        num_stops_per_route = 8
        route_stops = []
        
        # Select stops in different areas of the grid
        if bus_id < 2:  # North-south routes
            stops = [stop_id for stop_id, stop in self.city.stops.items() 
                    if stop.x < self.grid_size // 2]
        elif bus_id < 4:  # East-west routes
            stops = [stop_id for stop_id, stop in self.city.stops.items() 
                    if stop.y < self.grid_size // 2]
        else:  # Central routes
            stops = [stop_id for stop_id, stop in self.city.stops.items() 
                    if (self.grid_size // 4 < stop.x < 3 * self.grid_size // 4 and
                        self.grid_size // 4 < stop.y < 3 * self.grid_size // 4)]
        
        # Select subset for route
        if len(stops) >= num_stops_per_route:
            route_stops = random.sample(stops, num_stops_per_route)
        else:
            route_stops = stops
        
        return route_stops
    
    def _get_observation_space(self) -> spaces.Space:
        """Define observation space."""
        # Observation includes:
        # - Bus states (position, load, route info)
        # - Stop states (queue lengths, positions)
        # - Global state (time, traffic conditions)
        
        bus_state_dim = 6  # x, y, load_ratio, path_progress, next_stop_queue, eta
        stop_state_dim = 3  # x, y, queue_len
        global_state_dim = 2  # time_of_day, active_disruptions
        
        total_dim = (self.num_buses * bus_state_dim + 
                    self.num_stops * stop_state_dim + 
                    global_state_dim)
        
        return spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(total_dim,),
            dtype=np.float32
        )
    
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state."""
        if seed is not None:
            self.seed = seed
            random.seed(seed)
            np.random.seed(seed)
        
        # Reset components
        self.city = CityGrid(self.grid_size, self.num_stops, self.seed)
        self.buses = self._initialize_buses()
        self.riders = RiderDemand(self.city, self.seed)
        self.traffic_manager = TrafficManager(self.city)
        self.reward_calculator = RewardCalculator()
        
        # Reset state
        self.current_time = 0.0
        self.previous_state = None
        self.episode_length = 0
        
        observation = self._get_observation()
        info = {}
        
        return observation, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """Execute one environment step."""
        # Store previous state for reward calculation
        self.previous_state = self._store_bus_state()
        
        # Apply actions to buses
        self._apply_actions(action)
        
        # Update environment
        self._update_environment()
        
        # Calculate reward
        reward, reward_components = self.reward_calculator.calculate_reward(
            self.buses, self.riders, self.previous_state
        )
        
        # Get observation
        observation = self._get_observation()
        
        # Check if episode is done
        terminated = self.episode_length >= self.max_episode_length
        truncated = False  # We don't use truncation in this environment
        
        # Info dictionary
        info = {
            'reward_components': reward_components,
            'time': self.current_time,
            'episode_length': self.episode_length,
            'active_disruptions': self.traffic_manager.get_active_disruption_info()
        }
        
        self.episode_length += 1
        
        return observation, reward, terminated, truncated, info
    
    def _apply_actions(self, actions: np.ndarray):
        """Apply actions to buses."""
        for i, action in enumerate(actions):
            if i < len(self.buses):
                bus = self.buses[i]
                bus_action = BusAction(action)
                bus.last_action = bus_action
                
                self._execute_bus_action(bus, bus_action)
    
    def _execute_bus_action(self, bus: Bus, action: BusAction):
        """Execute a specific action for a bus."""
        if action == BusAction.CONTINUE:
            # Continue on current route (no change needed)
            pass
            
        elif action == BusAction.GO_TO_HIGH_DEMAND:
            # Redirect to high-demand stop
            high_demand_stops = self.riders.get_stop_demand_ranking()[:3]
            if high_demand_stops:
                target_stop_id = high_demand_stops[0][0]
                # Create new route to target stop
                current_pos = (int(bus.x), int(bus.y))
                target_pos = (self.city.stops[target_stop_id].x, 
                            self.city.stops[target_stop_id].y)
                path = self.city.get_shortest_path(current_pos, target_pos)
                
                # Convert path to route (find stops along path)
                new_route = []
                for pos in path:
                    for stop_id, stop in self.city.stops.items():
                        if stop.x == pos[0] and stop.y == pos[1]:
                            if stop_id not in new_route:
                                new_route.append(stop_id)
                
                bus.replan_route(self.city, new_route)
                
        elif action == BusAction.SKIP_LOW_DEMAND:
            # Skip current stop if low demand
            if bus.route and bus.path_index < len(bus.path):
                # Find current stop
                current_pos = (int(bus.x), int(bus.y))
                for stop_id, stop in self.city.stops.items():
                    if stop.x == current_pos[0] and stop.y == current_pos[1]:
                        if stop.queue_len < 5:  # Low demand threshold
                            # Skip to next stop in route
                            if stop_id in bus.route:
                                current_idx = bus.route.index(stop_id)
                                if current_idx < len(bus.route) - 1:
                                    next_stop = bus.route[current_idx + 1]
                                    next_pos = (self.city.stops[next_stop].x, 
                                              self.city.stops[next_stop].y)
                                    path = self.city.get_shortest_path(current_pos, next_pos)
                                    bus.path = path
                                    bus.path_index = 0
                        break
                        
        elif action == BusAction.SHORT_HOLD:
            # Hold at current position briefly
            # This is implemented by not updating position for a few steps
            pass  # Will be handled in position update
    
    def _update_environment(self):
        """Update all environment components."""
        # Update time
        self.current_time += self.dt
        
        # Generate new riders
        self.riders.generate_arrivals(self.current_time, self.dt)
        
        # Update traffic disruptions
        self.traffic_manager.update_disruptions(self.current_time)
        
        # Update buses
        for bus in self.buses:
            bus.update_position(self.city, self.dt)
            
            # Load/unload passengers at stops
            bus.load_passengers(self.city)
            
            # Handle route completion
            if bus.path_index >= len(bus.path) and bus.route:
                # Reached end of route, restart from beginning
                bus.set_route(self.city, bus.route)
        
        # Update rider wait times
        self.riders.update_wait_times(self.current_time, self.dt)
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation vector."""
        obs = []
        
        # Bus states
        for bus in self.buses:
            bus_state = bus.get_state_vector(self.city)
            obs.extend(bus_state)
        
        # Stop states
        for stop in self.city.stops.values():
            stop_state = [
                stop.x / self.grid_size,  # Normalized position
                stop.y / self.grid_size,
                stop.queue_len / 50.0  # Normalized queue length
            ]
            obs.extend(stop_state)
        
        # Global state
        time_of_day = (self.current_time % (24 * 3600)) / (24 * 3600)  # Normalized
        active_disruptions = len(self.traffic_manager.active_disruptions) / 10.0  # Normalized
        
        obs.extend([time_of_day, active_disruptions])
        
        return np.array(obs, dtype=np.float32)
    
    def _store_bus_state(self) -> Dict:
        """Store current bus state for reward calculation."""
        state = {}
        for bus in self.buses:
            state[bus.id] = {
                'fuel_km': bus.fuel_km,
                'load': bus.load,
                'position': (bus.x, bus.y)
            }
        return state
    
    def render(self, mode='human'):
        """Render environment (placeholder)."""
        pass
    
    def close(self):
        """Clean up environment."""
        pass
    
    # Additional methods for demo control
    
    def set_baseline_mode(self, baseline: bool):
        """Switch between RL and baseline modes."""
        self.baseline_mode = baseline
    
    def trigger_disruption(self, disruption_type: str, **kwargs):
        """Trigger a traffic disruption."""
        if disruption_type == "closure":
            edge = self.traffic_manager.get_random_central_edge()
            return self.traffic_manager.create_road_closure(
                edge[0], edge[1], current_time=self.current_time
            )
        elif disruption_type == "traffic":
            edge = self.traffic_manager.get_random_central_edge()
            return self.traffic_manager.create_traffic_slowdown(
                edge[0], edge[1], current_time=self.current_time
            )
        elif disruption_type == "surge":
            stops = self.traffic_manager.get_high_demand_stops(3)
            return self.traffic_manager.create_demand_surge(
                stops, current_time=self.current_time
            )
    
    def get_kpis(self) -> Dict[str, float]:
        """Get current performance metrics."""
        return self.reward_calculator.get_performance_metrics(self.riders, self.buses)
    
    def get_state_for_ui(self) -> Dict:
        """Get environment state for UI display."""
        return {
            'time': self.current_time,
            'buses': [
                {
                    'id': bus.id,
                    'x': bus.x,
                    'y': bus.y,
                    'load': bus.load,
                    'capacity': bus.capacity,
                    'mode': bus.mode
                }
                for bus in self.buses
            ],
            'stops': [
                {
                    'id': stop.id,
                    'x': stop.x,
                    'y': stop.y,
                    'queue_len': stop.queue_len
                }
                for stop in self.city.stops.values()
            ],
            'kpis': self.get_kpis(),
            'active_disruptions': self.traffic_manager.get_active_disruption_info()
        }
