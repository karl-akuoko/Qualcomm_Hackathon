"""
Traffic management and disruption simulation.
Handles road closures, traffic slowdowns, and surge events.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import random


class DisruptionType(Enum):
    """Types of traffic disruptions."""
    ROAD_CLOSURE = "closure"
    TRAFFIC_SLOWDOWN = "traffic"
    DEMAND_SURGE = "surge"


@dataclass
class Disruption:
    """Traffic disruption event."""
    id: str
    type: DisruptionType
    start_time: float
    duration: float
    affected_edges: List[Tuple[Tuple[int, int], Tuple[int, int]]]
    affected_stops: List[int]
    severity: float = 1.0  # 1.0 = normal, >1.0 = worse
    params: Dict = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = {}


class TrafficManager:
    """Manages traffic disruptions and their effects."""
    
    def __init__(self, city):
        self.city = city
        self.active_disruptions: Dict[str, Disruption] = {}
        self.disruption_history: List[Disruption] = []
        self.next_disruption_id = 0
    
    def create_road_closure(self, 
                          from_pos: Tuple[int, int], 
                          to_pos: Tuple[int, int],
                          duration: float = 600.0,  # 10 minutes
                          current_time: float = 0.0) -> str:
        """Create a road closure disruption."""
        disruption_id = f"closure_{self.next_disruption_id}"
        self.next_disruption_id += 1
        
        disruption = Disruption(
            id=disruption_id,
            type=DisruptionType.ROAD_CLOSURE,
            start_time=current_time,
            duration=duration,
            affected_edges=[(from_pos, to_pos)],
            affected_stops=[],
            severity=float('inf'),  # Completely closed
            params={'closed': True}
        )
        
        self.active_disruptions[disruption_id] = disruption
        self.city.close_road(from_pos, to_pos)
        
        return disruption_id
    
    def create_traffic_slowdown(self,
                              from_pos: Tuple[int, int],
                              to_pos: Tuple[int, int],
                              factor: float = 3.0,
                              duration: float = 300.0,  # 5 minutes
                              current_time: float = 0.0) -> str:
        """Create a traffic slowdown disruption."""
        disruption_id = f"traffic_{self.next_disruption_id}"
        self.next_disruption_id += 1
        
        disruption = Disruption(
            id=disruption_id,
            type=DisruptionType.TRAFFIC_SLOWDOWN,
            start_time=current_time,
            duration=duration,
            affected_edges=[(from_pos, to_pos)],
            affected_stops=[],
            severity=factor,
            params={'factor': factor}
        )
        
        self.active_disruptions[disruption_id] = disruption
        self.city.set_traffic_factor(from_pos, to_pos, factor)
        
        return disruption_id
    
    def create_demand_surge(self,
                          stop_ids: List[int],
                          surge_factor: float = 3.0,
                          duration: float = 600.0,  # 10 minutes
                          current_time: float = 0.0) -> str:
        """Create a demand surge at specific stops."""
        disruption_id = f"surge_{self.next_disruption_id}"
        self.next_disruption_id += 1
        
        disruption = Disruption(
            id=disruption_id,
            type=DisruptionType.DEMAND_SURGE,
            start_time=current_time,
            duration=duration,
            affected_edges=[],
            affected_stops=stop_ids,
            severity=surge_factor,
            params={'surge_factor': surge_factor, 'affected_stops': stop_ids}
        )
        
        self.active_disruptions[disruption_id] = disruption
        
        # Apply surge effect to stops
        for stop_id in stop_ids:
            if stop_id in self.city.stops:
                # Add immediate surge to queue
                self.city.stops[stop_id].queue_len += int(20 * surge_factor)
        
        return disruption_id
    
    def update_disruptions(self, current_time: float):
        """Update active disruptions and remove expired ones."""
        expired_disruptions = []
        
        for disruption_id, disruption in self.active_disruptions.items():
            if current_time >= disruption.start_time + disruption.duration:
                expired_disruptions.append(disruption_id)
            else:
                # Update ongoing disruption effects
                self._apply_disruption_effects(disruption, current_time)
        
        # Remove expired disruptions
        for disruption_id in expired_disruptions:
            disruption = self.active_disruptions[disruption_id]
            self._remove_disruption_effects(disruption)
            self.disruption_history.append(disruption)
            del self.active_disruptions[disruption_id]
    
    def _apply_disruption_effects(self, disruption: Disruption, current_time: float):
        """Apply ongoing effects of a disruption."""
        if disruption.type == DisruptionType.DEMAND_SURGE:
            # Continue adding surge demand
            for stop_id in disruption.affected_stops:
                if stop_id in self.city.stops:
                    # Add periodic surge arrivals
                    if random.random() < 0.1:  # 10% chance per update
                        surge_arrivals = int(disruption.severity * 2)
                        self.city.stops[stop_id].queue_len += surge_arrivals
    
    def _remove_disruption_effects(self, disruption: Disruption):
        """Remove effects when disruption ends."""
        if disruption.type == DisruptionType.ROAD_CLOSURE:
            # Reopen roads
            for from_pos, to_pos in disruption.affected_edges:
                self.city.reopen_road(from_pos, to_pos)
        
        elif disruption.type == DisruptionType.TRAFFIC_SLOWDOWN:
            # Reset traffic factors
            for from_pos, to_pos in disruption.affected_edges:
                self.city.set_traffic_factor(from_pos, to_pos, 1.0)
        
        # Demand surges naturally decay as riders are picked up
    
    def get_active_disruption_info(self) -> List[Dict]:
        """Get information about currently active disruptions."""
        info = []
        for disruption in self.active_disruptions.values():
            info.append({
                'id': disruption.id,
                'type': disruption.type.value,
                'severity': disruption.severity,
                'affected_edges': disruption.affected_edges,
                'affected_stops': disruption.affected_stops,
                'params': disruption.params
            })
        return info
    
    def clear_all_disruptions(self):
        """Clear all active disruptions."""
        for disruption in self.active_disruptions.values():
            self._remove_disruption_effects(disruption)
            self.disruption_history.append(disruption)
        
        self.active_disruptions.clear()
    
    def get_random_central_edge(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Get a random edge in the central area for disruptions."""
        # Focus on central area (8x8 in the middle of 20x20 grid)
        start_x = random.randint(6, 13)
        start_y = random.randint(6, 13)
        
        # Choose direction (horizontal or vertical)
        if random.random() < 0.5:
            # Horizontal edge
            end_x = start_x + 1
            end_y = start_y
        else:
            # Vertical edge
            end_x = start_x
            end_y = start_y + 1
        
        return (start_x, start_y), (end_x, end_y)
    
    def get_high_demand_stops(self, num_stops: int = 3) -> List[int]:
        """Get stops with highest current demand."""
        stop_demands = [(stop_id, stop.queue_len) 
                       for stop_id, stop in self.city.stops.items()]
        stop_demands.sort(key=lambda x: x[1], reverse=True)
        return [stop_id for stop_id, _ in stop_demands[:num_stops]]
