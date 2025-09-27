import numpy as np
from typing import Dict, List
from bus import BusFleet
from riders import RiderQueue

class RewardCalculator:
    """Calculate reward for RL policy based on system performance"""
    
    def __init__(self):
        self.prev_stats = None
        
        # Reward weights (as specified in MVP)
        self.wait_weight = -1.0        # -avg_wait
        self.overcrowd_weight = -2.0   # -2×overcrowd
        self.distance_weight = -0.1    # -0.1×extra_distance
        self.replan_weight = -0.05     # -0.05×replan
        
        # Baseline values for normalization
        self.baseline_avg_wait = 10.0
        self.baseline_load_std = 5.0
        self.baseline_distance_per_bus = 2.0
        
    def calculate_reward(self, bus_fleet: BusFleet, rider_queue: RiderQueue, 
                        current_time: float) -> float:
        """Calculate reward based on current system state"""
        
        # Get current statistics
        wait_stats = rider_queue.get_wait_time_stats()
        fleet_stats = bus_fleet.get_fleet_stats()
        
        # Wait time component
        avg_wait = wait_stats["avg"]
        normalized_wait = avg_wait / self.baseline_avg_wait
        wait_reward = self.wait_weight * normalized_wait
        
        # Overcrowding component (load standard deviation)
        load_std = fleet_stats["load_std"]
        normalized_overcrowd = load_std / self.baseline_load_std
        overcrowd_reward = self.overcrowd_weight * normalized_overcrowd
        
        # Distance component (encourage efficiency)
        avg_distance = fleet_stats["total_distance"] / len(bus_fleet.buses)
        if self.prev_stats:
            prev_avg_distance = self.prev_stats["total_distance"] / len(bus_fleet.buses)
            extra_distance = max(0, avg_distance - prev_avg_distance - self.baseline_distance_per_bus)
        else:
            extra_distance = 0.0
        distance_reward = self.distance_weight * extra_distance
        
        # Replan component (encourage stable policies)
        avg_replans = fleet_stats["avg_replans"]
        if self.prev_stats:
            prev_avg_replans = self.prev_stats.get("avg_replans", 0)
            new_replans = max(0, avg_replans - prev_avg_replans)
        else:
            new_replans = 0.0
        replan_reward = self.replan_weight * new_replans
        
        # Total reward
        total_reward = wait_reward + overcrowd_reward + distance_reward + replan_reward
        
        # Store current stats for next calculation
        self.prev_stats = fleet_stats.copy()
        self.prev_stats.update(wait_stats)
        
        return total_reward
    
    def get_reward_breakdown(self, bus_fleet: BusFleet, rider_queue: RiderQueue, 
                           current_time: float) -> Dict[str, float]:
        """Get detailed breakdown of reward components"""
        
        wait_stats = rider_queue.get_wait_time_stats()
        fleet_stats = bus_fleet.get_fleet_stats()
        
        # Calculate components
        avg_wait = wait_stats["avg"]
        normalized_wait = avg_wait / self.baseline_avg_wait
        wait_reward = self.wait_weight * normalized_wait
        
        load_std = fleet_stats["load_std"]
        normalized_overcrowd = load_std / self.baseline_load_std
        overcrowd_reward = self.overcrowd_weight * normalized_overcrowd
        
        avg_distance = fleet_stats["total_distance"] / len(bus_fleet.buses)
        if self.prev_stats:
            prev_avg_distance = self.prev_stats["total_distance"] / len(bus_fleet.buses)
            extra_distance = max(0, avg_distance - prev_avg_distance - self.baseline_distance_per_bus)
        else:
            extra_distance = 0.0
        distance_reward = self.distance_weight * extra_distance
        
        avg_replans = fleet_stats["avg_replans"]
        if self.prev_stats:
            prev_avg_replans = self.prev_stats.get("avg_replans", 0)
            new_replans = max(0, avg_replans - prev_avg_replans)
        else:
            new_replans = 0.0
        replan_reward = self.replan_weight * new_replans
        
        total_reward = wait_reward + overcrowd_reward + distance_reward + replan_reward
        
        return {
            "total": total_reward,
            "wait": wait_reward,
            "overcrowd": overcrowd_reward,
            "distance": distance_reward,
            "replan": replan_reward,
            "metrics": {
                "avg_wait": avg_wait,
                "load_std": load_std,
                "extra_distance": extra_distance,
                "new_replans": new_replans
            }
        }
    
    def reset(self):
        """Reset reward calculator state"""
        self.prev_stats = None