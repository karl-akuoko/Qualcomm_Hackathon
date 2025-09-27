import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import math

class TimeOfDay(Enum):
    MORNING_RUSH = "morning_rush"    # 7-9 AM
    MIDDAY = "midday"               # 9 AM - 4 PM
    EVENING_RUSH = "evening_rush"   # 4-7 PM
    NIGHT = "night"                 # 7 PM - 7 AM

@dataclass
class Rider:
    id: int
    origin: int
    destination: int
    arrival_time: float
    wait_time: float = 0.0
    picked_up: bool = False
    
    def update_wait_time(self, current_time: float):
        """Update rider wait time"""
        if not self.picked_up:
            self.wait_time = current_time - self.arrival_time

class RiderGenerator:
    """Generates riders with time-of-day patterns and demand surges"""
    
    def __init__(self, stops: Dict, seed: int = 42):
        self.stops = stops
        self.stop_ids = list(stops.keys())
        self.rider_counter = 0
        
        np.random.seed(seed)
        
        # Time-of-day arrival rates (riders per minute per stop)
        self.base_rates = {
            TimeOfDay.MORNING_RUSH: 0.8,
            TimeOfDay.MIDDAY: 0.3,
            TimeOfDay.EVENING_RUSH: 0.7,
            TimeOfDay.NIGHT: 0.1
        }
        
        # Stop-specific multipliers (simulate popular destinations)
        self.stop_popularity = self._initialize_stop_popularity()
        
        # Destination preferences by time of day
        self.destination_prefs = self._initialize_destination_preferences()
        
        # Current surge zones
        self.surge_zones: Dict[int, float] = {}  # stop_id -> multiplier
        
    def _initialize_stop_popularity(self) -> Dict[int, float]:
        """Initialize stop popularity multipliers"""
        popularity = {}
        for stop_id in self.stop_ids:
            stop = self.stops[stop_id]
            
            # Central locations are more popular
            center_x, center_y = 10, 10
            distance_from_center = math.sqrt((stop.x - center_x)**2 + (stop.y - center_y)**2)
            
            # Popularity decreases with distance from center
            popularity[stop_id] = max(0.5, 2.0 - distance_from_center / 10)
            
        return popularity
    
    def _initialize_destination_preferences(self) -> Dict[TimeOfDay, Dict[int, float]]:
        """Initialize destination preferences by time of day"""
        prefs = {}
        
        for time_period in TimeOfDay:
            prefs[time_period] = {}
            
            for stop_id in self.stop_ids:
                stop = self.stops[stop_id]
                
                if time_period == TimeOfDay.MORNING_RUSH:
                    # Morning: people go to business district (center-bottom)
                    business_center_x, business_center_y = 10, 15
                    dist = math.sqrt((stop.x - business_center_x)**2 + (stop.y - business_center_y)**2)
                    prefs[time_period][stop_id] = max(0.3, 2.0 - dist / 8)
                    
                elif time_period == TimeOfDay.EVENING_RUSH:
                    # Evening: people go to residential areas (spread out)
                    prefs[time_period][stop_id] = 1.0  # More uniform
                    
                else:
                    # Midday/Night: mixed patterns
                    prefs[time_period][stop_id] = self.stop_popularity[stop_id]
        
        return prefs
    
    def get_time_of_day(self, sim_time: float) -> TimeOfDay:
        """Convert simulation time to time of day"""
        # Assume sim_time is in minutes, cycle every 24 hours (1440 minutes)
        hour_of_day = (sim_time / 60) % 24
        
        if 7 <= hour_of_day < 9:
            return TimeOfDay.MORNING_RUSH
        elif 9 <= hour_of_day < 16:
            return TimeOfDay.MIDDAY
        elif 16 <= hour_of_day < 19:
            return TimeOfDay.EVENING_RUSH
        else:
            return TimeOfDay.NIGHT
    
    def add_surge(self, stop_id: int, multiplier: float):
        """Add a demand surge at a specific stop"""
        self.surge_zones[stop_id] = multiplier
    
    def remove_surge(self, stop_id: int):
        """Remove surge from a stop"""
        if stop_id in self.surge_zones:
            del self.surge_zones[stop_id]
    
    def clear_surges(self):
        """Clear all surges"""
        self.surge_zones.clear()
    
    def generate_arrivals(self, current_time: float, time_step: float) -> List[Rider]:
        """Generate new rider arrivals in the time step"""
        new_riders = []
        time_period = self.get_time_of_day(current_time)
        base_rate = self.base_rates[time_period]
        
        for stop_id in self.stop_ids:
            # Calculate arrival rate for this stop
            rate = base_rate * self.stop_popularity[stop_id]
            
            # Apply surge multiplier if active
            if stop_id in self.surge_zones:
                rate *= self.surge_zones[stop_id]
            
            # Generate arrivals using Poisson process
            # Expected arrivals in time_step
            lambda_param = rate * time_step
            num_arrivals = np.random.poisson(lambda_param)
            
            for _ in range(num_arrivals):
                destination = self._choose_destination(stop_id, time_period)
                if destination != stop_id:  # Don't create riders with same origin/destination
                    rider = Rider(
                        id=self.rider_counter,
                        origin=stop_id,
                        destination=destination,
                        arrival_time=current_time + np.random.uniform(0, time_step)
                    )
                    new_riders.append(rider)
                    self.rider_counter += 1
        
        return new_riders
    
    def _choose_destination(self, origin: int, time_period: TimeOfDay) -> int:
        """Choose destination based on time of day preferences"""
        # Get all possible destinations (excluding origin)
        possible_destinations = [s for s in self.stop_ids if s != origin]
        
        # Get weights based on time period preferences
        weights = [self.destination_prefs[time_period][stop_id] for stop_id in possible_destinations]
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            probs = [w / total_weight for w in weights]
            return np.random.choice(possible_destinations, p=probs)
        else:
            return np.random.choice(possible_destinations)

class RiderQueue:
    """Manages rider queues at bus stops"""
    
    def __init__(self):
        self.queues: Dict[int, List[Rider]] = {}  # stop_id -> list of riders
        self.picked_up_riders: List[Rider] = []
    
    def add_riders(self, riders: List[Rider]):
        """Add new riders to their origin stop queues"""
        for rider in riders:
            if rider.origin not in self.queues:
                self.queues[rider.origin] = []
            self.queues[rider.origin].append(rider)
    
    def get_queue_length(self, stop_id: int) -> int:
        """Get number of waiting riders at a stop"""
        return len(self.queues.get(stop_id, []))
    
    def pick_up_riders(self, stop_id: int, capacity: int, current_time: float) -> List[Rider]:
        """Pick up riders from a stop (up to capacity)"""
        if stop_id not in self.queues:
            return []
        
        # Pick up riders (FIFO)
        riders_to_pickup = self.queues[stop_id][:capacity]
        self.queues[stop_id] = self.queues[stop_id][capacity:]
        
        # Mark as picked up and update wait times
        for rider in riders_to_pickup:
            rider.picked_up = True
            rider.update_wait_time(current_time)
        
        self.picked_up_riders.extend(riders_to_pickup)
        return riders_to_pickup
    
    def update_wait_times(self, current_time: float):
        """Update wait times for all waiting riders"""
        for stop_riders in self.queues.values():
            for rider in stop_riders:
                rider.update_wait_time(current_time)
    
    def get_waiting_riders(self) -> List[Rider]:
        """Get all currently waiting riders"""
        waiting = []
        for stop_riders in self.queues.values():
            waiting.extend(stop_riders)
        return waiting
    
    def get_total_wait_time(self) -> float:
        """Calculate total wait time across all riders"""
        total_wait = 0.0
        
        # Waiting riders
        for rider in self.get_waiting_riders():
            total_wait += rider.wait_time
        
        # Picked up riders
        for rider in self.picked_up_riders:
            total_wait += rider.wait_time
        
        return total_wait
    
    def get_wait_time_stats(self) -> Dict[str, float]:
        """Get wait time statistics"""
        all_wait_times = []
        
        # Include waiting riders
        for rider in self.get_waiting_riders():
            all_wait_times.append(rider.wait_time)
        
        # Include picked up riders
        for rider in self.picked_up_riders:
            all_wait_times.append(rider.wait_time)
        
        if not all_wait_times:
            return {"avg": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0}
        
        all_wait_times.sort()
        n = len(all_wait_times)
        
        return {
            "avg": np.mean(all_wait_times),
            "p90": all_wait_times[int(0.9 * n)] if n > 0 else 0.0,
            "p95": all_wait_times[int(0.95 * n)] if n > 0 else 0.0,
            "max": max(all_wait_times)
        }
    
    def reset(self):
        """Reset all queues and riders"""
        self.queues.clear()
        self.picked_up_riders.clear()
