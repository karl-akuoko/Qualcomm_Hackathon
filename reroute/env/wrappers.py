import gymnasium as gym
import numpy as np
from gymnasium import spaces
from typing import Dict, List, Tuple, Any
from .city import ManhattanGrid
from .riders import RiderGenerator, RiderQueue
from .bus import BusFleet, BusMode, BusAction
from .reward import RewardCalculator

class BusDispatchEnv(gym.Env):
    """Gym environment for bus dispatching RL"""
    
    def __init__(self, 
                 grid_size: Tuple[int, int] = (20, 20),
                 num_stops: int = 32,
                 num_buses: int = 6,
                 time_step: float = 0.5,  # 30 seconds
                 max_episode_time: float = 120.0,  # 2 hours
                 seed: int = 42):
        
        super().__init__()
        
        self.grid_size = grid_size
        self.num_stops = num_stops
        self.num_buses = num_buses
        self.time_step = time_step
        self.max_episode_time = max_episode_time
        self.seed = seed
        
        # Initialize city components
        self.city_grid = ManhattanGrid(grid_size[0], grid_size[1], num_stops)
        self.rider_generator = RiderGenerator(self.city_grid.stops, seed)
        self.rider_queue = RiderQueue()
        self.bus_fleet = BusFleet(self.city_grid, num_buses)
        self.reward_calculator = RewardCalculator()
        
        # Episode state
        self.current_time = 0.0
        self.episode_step = 0
        
        # Action space: one action per bus
        # Actions: {CONTINUE=0, HIGH_DEMAND=1, SKIP_LOW=2, SHORT_HOLD=3}
        self.action_space = spaces.MultiDiscrete([4] * num_buses)
        
        # Observation space: bus states + stop queues
        bus_features = 5  # x, y, load, is_moving, hold_time
        stop_features = 1  # queue_length
        obs_size = num_buses * bus_features + num_stops * stop_features
        
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(obs_size,), dtype=np.float32
        )
        
        # Baseline comparison
        self.baseline_fleet = BusFleet(self.city_grid, num_buses)
        self.baseline_queue = RiderQueue()
        self.baseline_stats_history = []
        
    def reset(self, seed: int = None) -> np.ndarray:
        """Reset environment to initial state"""
        if seed is not None:
            self.seed = seed
            np.random.seed(seed)
            self.rider_generator = RiderGenerator(self.city_grid.stops, seed)
        
        # Reset time and episode
        self.current_time = 0.0
        self.episode_step = 0
        
        # Reset components
        self.rider_queue.reset()
        self.bus_fleet = BusFleet(self.city_grid, self.num_buses)
        self.bus_fleet.set_mode(BusMode.RL)
        self.reward_calculator.reset()
        
        # Reset baseline
        self.baseline_queue.reset()
        self.baseline_fleet = BusFleet(self.city_grid, self.num_buses)
        self.baseline_fleet.set_mode(BusMode.STATIC)
        self.baseline_stats_history.clear()
        
        # Clear any disruptions
        self.rider_generator.clear_surges()
        self._reset_all_edges()
        
        return self._get_observation()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute one step in the environment"""
        
        # Apply RL actions
        self.bus_fleet.apply_rl_actions(action.tolist(), self.rider_queue, self.current_time)
        
        # Generate new riders
        new_riders = self.rider_generator.generate_arrivals(self.current_time, self.time_step)
        self.rider_queue.add_riders(new_riders)
        self.baseline_queue.add_riders([r for r in new_riders])  # Copy for baseline
        
        # Update bus movements
        self.bus_fleet.update_movement(self.time_step)
        self.baseline_fleet.update_movement(self.time_step)
        
        # Process stop arrivals (pickup/dropoff)
        self.bus_fleet.process_stop_arrivals(self.rider_queue, self.current_time)
        self.baseline_fleet.process_stop_arrivals(self.baseline_queue, self.current_time)
        
        # Update wait times
        self.rider_queue.update_wait_times(self.current_time)
        self.baseline_queue.update_wait_times(self.current_time)
        
        # Calculate reward
        reward = self.reward_calculator.calculate_reward(
            self.bus_fleet, self.rider_queue, self.current_time
        )
        
        # Update time
        self.current_time += self.time_step
        self.episode_step += 1
        
        # Check if episode is done
        done = self.current_time >= self.max_episode_time
        
        # Collect info
        info = self._get_info()
        
        return self._get_observation(), reward, done, info
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation"""
        return self.bus_fleet.get_state_vector(self.rider_queue)
    
    def _get_info(self) -> Dict[str, Any]:
        """Get episode information"""
        # RL stats
        rl_wait_stats = self.rider_queue.get_wait_time_stats()
        rl_fleet_stats = self.bus_fleet.get_fleet_stats()
        
        # Baseline stats
        baseline_wait_stats = self.baseline_queue.get_wait_time_stats()
        baseline_fleet_stats = self.baseline_fleet.get_fleet_stats()
        
        # Calculate improvements
        avg_wait_improvement = 0.0
        overcrowd_improvement = 0.0
        
        if baseline_wait_stats["avg"] > 0:
            avg_wait_improvement = (baseline_wait_stats["avg"] - rl_wait_stats["avg"]) / baseline_wait_stats["avg"]
        
        if baseline_fleet_stats["load_std"] > 0:
            overcrowd_improvement = (baseline_fleet_stats["load_std"] - rl_fleet_stats["load_std"]) / baseline_fleet_stats["load_std"]
        
        return {
            "time": self.current_time,
            "rl_stats": {
                "avg_wait": rl_wait_stats["avg"],
                "p90_wait": rl_wait_stats["p90"],
                "load_std": rl_fleet_stats["load_std"],
                "avg_utilization": rl_fleet_stats["avg_utilization"],
                "total_replans": rl_fleet_stats["total_replans"]
            },
            "baseline_stats": {
                "avg_wait": baseline_wait_stats["avg"],
                "p90_wait": baseline_wait_stats["p90"],
                "load_std": baseline_fleet_stats["load_std"],
                "avg_utilization": baseline_fleet_stats["avg_utilization"]
            },
            "improvements": {
                "avg_wait": avg_wait_improvement,
                "overcrowd": overcrowd_improvement
            }
        }
    
    def apply_disruption(self, disruption_type: str, params: Dict[str, Any]):
        """Apply external disruption to the system"""
        
        if disruption_type == "closure":
            # Close a road
            stop_ids = list(self.city_grid.stops.keys())
            if "stop_id" in params:
                center_stop = params["stop_id"]
            else:
                center_stop = np.random.choice(stop_ids)
            
            # Close edges around the stop
            neighbors = self.city_grid.get_neighbors(center_stop)
            for neighbor in neighbors[:2]:  # Close first 2 connections
                self.city_grid.close_edge(center_stop, neighbor)
        
        elif disruption_type == "traffic":
            # Add traffic to an area
            stop_ids = list(self.city_grid.stops.keys())
            if "stop_id" in params:
                center_stop = params["stop_id"]
            else:
                center_stop = np.random.choice(stop_ids)
            
            slowdown_factor = params.get("factor", 2.0)
            
            # Slow down edges around the stop
            neighbors = self.city_grid.get_neighbors(center_stop)
            for neighbor in neighbors:
                self.city_grid.slow_edge(center_stop, neighbor, slowdown_factor)
        
        elif disruption_type == "surge":
            # Create demand surge
            stop_ids = list(self.city_grid.stops.keys())
            if "stop_id" in params:
                surge_stop = params["stop_id"]
            else:
                surge_stop = np.random.choice(stop_ids)
            
            surge_multiplier = params.get("multiplier", 3.0)
            self.rider_generator.add_surge(surge_stop, surge_multiplier)
    
    def _reset_all_edges(self):
        """Reset all edges to normal conditions"""
        for (u, v), edge in self.city_grid.edges.items():
            self.city_grid.reset_edge(u, v)
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get complete system state for visualization"""
        buses_data = []
        for bus in self.bus_fleet.buses.values():
            buses_data.append({
                "id": bus.id,
                "x": bus.x,
                "y": bus.y,
                "load": bus.load,
                "capacity": bus.capacity,
                "next_stop": bus.next_stop,
                "is_moving": bus.is_moving,
                "mode": bus.mode.value
            })
        
        stops_data = []
        for stop_id, stop in self.city_grid.stops.items():
            queue_len = self.rider_queue.get_queue_length(stop_id)
            stops_data.append({
                "id": stop_id,
                "x": stop.x,
                "y": stop.y,
                "queue_len": queue_len,
                "eta_list": stop.eta_list.copy()
            })
        
        # Get KPIs
        wait_stats = self.rider_queue.get_wait_time_stats()
        fleet_stats = self.bus_fleet.get_fleet_stats()
        baseline_wait_stats = self.baseline_queue.get_wait_time_stats()
        baseline_fleet_stats = self.baseline_fleet.get_fleet_stats()
        
        return {
            "time": self.current_time,
            "buses": buses_data,
            "stops": stops_data,
            "kpi": {
                "avg_wait": wait_stats["avg"],
                "p90_wait": wait_stats["p90"],
                "load_std": fleet_stats["load_std"]
            },
            "baseline_kpi": {
                "avg_wait": baseline_wait_stats["avg"],
                "p90_wait": baseline_wait_stats["p90"],
                "load_std": baseline_fleet_stats["load_std"]
            }
        }
    
    def render(self, mode="human"):
        """Render environment (placeholder)"""
        if mode == "human":
            state = self.get_system_state()
            print(f"Time: {state['time']:.1f}")
            print(f"RL Avg Wait: {state['kpi']['avg_wait']:.2f}")
            print(f"Baseline Avg Wait: {state['baseline_kpi']['avg_wait']:.2f}")
            print("---")
