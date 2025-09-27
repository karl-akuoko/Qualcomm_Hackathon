"""
Reward function for the RL bus routing environment.
Implements the specified reward components: wait time, overcrowding, distance, and replanning.
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class RewardComponents:
    """Breakdown of reward components for analysis."""
    avg_wait: float = 0.0
    overcrowd_penalty: float = 0.0
    distance_penalty: float = 0.0
    replan_penalty: float = 0.0
    total: float = 0.0


class RewardCalculator:
    """Calculates rewards for the RL environment."""
    
    def __init__(self):
        # Reward weights (as specified in requirements)
        self.wait_weight = -1.0  # -avg_wait
        self.overcrowd_weight = -2.0  # -2×overcrowd
        self.distance_weight = -0.1  # -0.1×extra_distance
        self.replan_weight = -0.05  # -0.05×replan
        
        # Overcrowding threshold (percentage of capacity)
        self.overcrowd_threshold = 0.9  # 90% capacity
        
        # Tracking for rolling averages
        self.wait_times_history = []
        self.max_history_length = 1000
    
    def calculate_reward(self, 
                        buses: List,
                        riders,
                        previous_state: Dict = None) -> Tuple[float, RewardComponents]:
        """
        Calculate reward based on current state.
        
        Returns:
            reward: Total reward value
            components: Breakdown of reward components
        """
        components = RewardComponents()
        
        # 1. Average wait time component
        components.avg_wait = self._calculate_wait_penalty(riders)
        
        # 2. Overcrowding component
        components.overcrowd_penalty = self._calculate_overcrowd_penalty(buses)
        
        # 3. Extra distance component
        components.distance_penalty = self._calculate_distance_penalty(buses, previous_state)
        
        # 4. Replanning component
        components.replan_penalty = self._calculate_replan_penalty(buses)
        
        # Calculate total reward
        components.total = (
            self.wait_weight * components.avg_wait +
            self.overcrowd_weight * components.overcrowd_penalty +
            self.distance_weight * components.distance_penalty +
            self.replan_weight * components.replan_penalty
        )
        
        return components.total, components
    
    def _calculate_wait_penalty(self, riders) -> float:
        """Calculate average wait time penalty."""
        kpis = riders.get_kpis()
        avg_wait = kpis['avg_wait']
        
        # Add to history for rolling average
        self.wait_times_history.append(avg_wait)
        if len(self.wait_times_history) > self.max_history_length:
            self.wait_times_history.pop(0)
        
        return avg_wait
    
    def _calculate_overcrowd_penalty(self, buses: List) -> float:
        """Calculate overcrowding penalty."""
        if not buses:
            return 0.0
        
        overcrowd_minutes = 0.0
        
        for bus in buses:
            # Calculate overcrowding as percentage above threshold
            load_ratio = bus.load / bus.capacity if bus.capacity > 0 else 0.0
            
            if load_ratio > self.overcrowd_threshold:
                # Penalty proportional to how much over the threshold
                excess_ratio = load_ratio - self.overcrowd_threshold
                overcrowd_minutes += excess_ratio * 60.0  # Convert to "minutes"
        
        return overcrowd_minutes
    
    def _calculate_distance_penalty(self, buses: List, previous_state: Dict = None) -> float:
        """Calculate extra distance penalty."""
        if not buses or previous_state is None:
            return 0.0
        
        total_extra_distance = 0.0
        
        for bus in buses:
            if bus.id in previous_state:
                prev_fuel = previous_state[bus.id].get('fuel_km', 0.0)
                current_fuel = bus.fuel_km
                distance_traveled = current_fuel - prev_fuel
                
                # Assume minimum necessary distance per step
                min_distance = 0.001  # 1 meter per step minimum
                if distance_traveled > min_distance:
                    extra_distance = distance_traveled - min_distance
                    total_extra_distance += extra_distance
        
        return total_extra_distance
    
    def _calculate_replan_penalty(self, buses: List) -> float:
        """Calculate replanning penalty."""
        if not buses:
            return 0.0
        
        total_replans = sum(bus.replan_count for bus in buses)
        return float(total_replans)
    
    def get_performance_metrics(self, riders, buses: List) -> Dict[str, float]:
        """Get comprehensive performance metrics."""
        kpis = riders.get_kpis()
        
        # Calculate overcrowding metrics
        overcrowd_stops = 0
        total_overcrowd_ratio = 0.0
        
        for bus in buses:
            load_ratio = bus.load / bus.capacity if bus.capacity > 0 else 0.0
            if load_ratio > self.overcrowd_threshold:
                overcrowd_stops += 1
                total_overcrowd_ratio += load_ratio
        
        avg_overcrowd_ratio = total_overcrowd_ratio / len(buses) if buses else 0.0
        
        # Calculate replanning frequency
        total_replans = sum(bus.replan_count for bus in buses)
        replan_frequency = total_replans / len(buses) if buses else 0.0
        
        return {
            'avg_wait': kpis['avg_wait'],
            'p90_wait': kpis['p90_wait'],
            'load_std': kpis['load_std'],
            'overcrowd_stops': overcrowd_stops,
            'overcrowd_ratio': avg_overcrowd_ratio,
            'total_replans': total_replans,
            'replan_frequency': replan_frequency,
            'active_riders': kpis['active_riders'],
            'total_arrivals': kpis['total_arrivals'],
            'total_departures': kpis['total_departures']
        }
    
    def calculate_baseline_comparison(self, 
                                    rl_metrics: Dict[str, float],
                                    baseline_metrics: Dict[str, float]) -> Dict[str, float]:
        """Calculate improvement percentages vs baseline."""
        improvements = {}
        
        for metric in ['avg_wait', 'p90_wait', 'load_std', 'overcrowd_ratio']:
            if metric in rl_metrics and metric in baseline_metrics:
                rl_val = rl_metrics[metric]
                baseline_val = baseline_metrics[metric]
                
                if baseline_val > 0:
                    improvement = ((baseline_val - rl_val) / baseline_val) * 100
                    improvements[f'{metric}_improvement'] = improvement
                else:
                    improvements[f'{metric}_improvement'] = 0.0
        
        return improvements
    
    def reset(self):
        """Reset reward calculator state."""
        self.wait_times_history.clear()
