"""
Rider demand modeling for the bus routing simulation.
Handles passenger arrivals, wait times, and demand patterns.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random


@dataclass
class Rider:
    """Individual rider with origin, destination, and timing."""
    id: int
    origin_stop: int
    destination_stop: int
    arrival_time: float
    departure_time: Optional[float] = None
    wait_time: float = 0.0
    travel_time: float = 0.0


class RiderDemand:
    """Manages rider demand patterns and arrivals."""
    
    def __init__(self, city, seed: int = 42):
        self.city = city
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        
        # Rider tracking
        self.riders: Dict[int, Rider] = {}
        self.next_rider_id = 0
        self.completed_riders: List[Rider] = []
        
        # Demand patterns
        self.time_of_day_multipliers = self._create_time_of_day_patterns()
        
        # Statistics
        self.total_arrivals = 0
        self.total_departures = 0
        self.avg_wait_time = 0.0
        self.p90_wait_time = 0.0
        
    def _create_time_of_day_patterns(self) -> Dict[int, float]:
        """Create time-of-day arrival rate multipliers."""
        patterns = {}
        
        # Hourly multipliers (24-hour cycle)
        for hour in range(24):
            if 6 <= hour <= 8:  # Morning peak
                patterns[hour] = 2.5
            elif 17 <= hour <= 19:  # Evening peak
                patterns[hour] = 2.2
            elif 22 <= hour or hour <= 5:  # Night hours
                patterns[hour] = 0.3
            elif 12 <= hour <= 13:  # Lunch hour
                patterns[hour] = 1.3
            else:  # Normal hours
                patterns[hour] = 1.0
                
        return patterns
    
    def generate_arrivals(self, current_time: float, dt: float = 1.0) -> List[Rider]:
        """Generate new rider arrivals based on current time."""
        new_riders = []
        
        # Get current hour for time-of-day multiplier
        hour = int(current_time // 3600) % 24
        multiplier = self.time_of_day_multipliers.get(hour, 1.0)
        
        # Base arrival rate (riders per second per stop)
        base_rate = 0.05 * multiplier
        
        # Generate arrivals for each stop
        for stop_id, stop in self.city.stops.items():
            # Poisson process for arrivals
            arrival_rate = base_rate * dt
            num_arrivals = np.random.poisson(arrival_rate)
            
            for _ in range(num_arrivals):
                # Choose destination (weighted by distance)
                destination = self._choose_destination(stop_id)
                
                rider = Rider(
                    id=self.next_rider_id,
                    origin_stop=stop_id,
                    destination_stop=destination,
                    arrival_time=current_time
                )
                
                new_riders.append(rider)
                self.riders[self.next_rider_id] = rider
                self.next_rider_id += 1
                self.total_arrivals += 1
                
                # Add to stop queue
                stop.queue_len += 1
        
        return new_riders
    
    def _choose_destination(self, origin_stop: int) -> int:
        """Choose destination stop for a rider."""
        origin = self.city.stops[origin_stop]
        origin_pos = (origin.x, origin.y)
        
        # Weight destinations by distance (closer stops more likely)
        distances = []
        stop_ids = []
        
        for stop_id, stop in self.city.stops.items():
            if stop_id != origin_stop:
                distance = abs(stop.x - origin.x) + abs(stop.y - origin.y)
                # Inverse distance weighting (closer = more likely)
                weight = 1.0 / (distance + 1)
                distances.append(weight)
                stop_ids.append(stop_id)
        
        # Choose based on weights
        if stop_ids:
            destination = random.choices(stop_ids, weights=distances)[0]
        else:
            destination = origin_stop
            
        return destination
    
    def update_wait_times(self, current_time: float, dt: float):
        """Update wait times for all waiting riders."""
        for rider in self.riders.values():
            if rider.departure_time is None:  # Still waiting
                rider.wait_time += dt
    
    def board_bus(self, rider_ids: List[int], bus_id: int, current_time: float):
        """Mark riders as boarded on a bus."""
        for rider_id in rider_ids:
            if rider_id in self.riders:
                rider = self.riders[rider_id]
                rider.departure_time = current_time
                rider.travel_time = 0.0
    
    def alight_bus(self, rider_ids: List[int], current_time: float):
        """Mark riders as alighted and complete their journey."""
        for rider_id in rider_ids:
            if rider_id in self.riders:
                rider = self.riders[rider_id]
                if rider.departure_time is not None:
                    rider.travel_time = current_time - rider.departure_time
                    self.completed_riders.append(rider)
                    del self.riders[rider_id]
                    self.total_departures += 1
    
    def update_travel_times(self, dt: float):
        """Update travel times for riders currently on buses."""
        for rider in self.riders.values():
            if rider.departure_time is not None:  # On a bus
                rider.travel_time += dt
    
    def get_kpis(self) -> Dict[str, float]:
        """Calculate current KPIs."""
        # Average wait time (last 100 completed riders)
        recent_riders = self.completed_riders[-100:] if len(self.completed_riders) >= 100 else self.completed_riders
        
        if recent_riders:
            wait_times = [r.wait_time for r in recent_riders]
            self.avg_wait_time = np.mean(wait_times)
            self.p90_wait_time = np.percentile(wait_times, 90)
        else:
            self.avg_wait_time = 0.0
            self.p90_wait_time = 0.0
        
        # Load standard deviation across stops
        queue_lengths = [stop.queue_len for stop in self.city.stops.values()]
        load_std = np.std(queue_lengths) if queue_lengths else 0.0
        
        return {
            'avg_wait': self.avg_wait_time,
            'p90_wait': self.p90_wait_time,
            'load_std': load_std,
            'total_arrivals': self.total_arrivals,
            'total_departures': self.total_departures,
            'active_riders': len(self.riders)
        }
    
    def create_surge(self, stop_ids: List[int], surge_factor: float = 3.0, duration: float = 300.0):
        """Create a demand surge at specific stops."""
        # This would be implemented to temporarily increase arrival rates
        # at specified stops for demonstration purposes
        pass
    
    def get_stop_demand_ranking(self) -> List[Tuple[int, int]]:
        """Get stops ranked by current demand (queue length)."""
        stop_demands = [(stop_id, stop.queue_len) for stop_id, stop in self.city.stops.items()]
        return sorted(stop_demands, key=lambda x: x[1], reverse=True)
    
    def reset(self):
        """Reset all rider data."""
        self.riders.clear()
        self.completed_riders.clear()
        self.next_rider_id = 0
        self.total_arrivals = 0
        self.total_departures = 0
        self.avg_wait_time = 0.0
        self.p90_wait_time = 0.0
        
        # Reset stop queues
        for stop in self.city.stops.values():
            stop.queue_len = 0
