import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math

class TrafficCondition(Enum):
    FREE_FLOW = "free_flow"
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    GRIDLOCK = "gridlock"

@dataclass
class TrafficZone:
    """Represents a traffic-affected zone"""
    center_x: int
    center_y: int
    radius: int
    severity: float  # 1.0 = normal, 2.0 = 2x slower, etc.
    duration: float  # minutes remaining
    zone_type: str   # "construction", "accident", "event", etc.

class TrafficModel:
    """Models dynamic traffic conditions across the city grid"""
    
    def __init__(self, grid_width: int, grid_height: int):
        self.grid_width = grid_width
        self.grid_height = grid_height
        
        # Base traffic patterns by time and location
        self.base_congestion = np.ones((grid_width, grid_height))
        self.time_of_day_factors = {}
        self.active_zones: List[TrafficZone] = []
        
        # Initialize time-of-day patterns
        self._initialize_traffic_patterns()
    
    def _initialize_traffic_patterns(self):
        """Initialize realistic traffic patterns for Manhattan-style grid"""
        
        # Morning rush (7-9 AM): Heavy inbound to business district
        morning_pattern = np.ones((self.grid_width, self.grid_height))
        
        # Business district (bottom half of grid) gets congested
        for x in range(self.grid_width):
            for y in range(self.grid_height // 2, self.grid_height):
                # Distance from center business area
                business_center_x = self.grid_width // 2
                business_center_y = int(self.grid_height * 0.75)
                distance = math.sqrt((x - business_center_x)**2 + (y - business_center_y)**2)
                
                # Closer to business center = more congestion
                congestion_factor = 1.0 + 0.8 * math.exp(-distance / 5)
                morning_pattern[x, y] = congestion_factor
        
        # Evening rush (4-7 PM): Heavy outbound from business district
        evening_pattern = morning_pattern.copy()
        
        # Add congestion to major arteries (avenues)
        for x in range(0, self.grid_width, 4):  # Major avenues every 4 blocks
            morning_pattern[x, :] *= 1.3
            evening_pattern[x, :] *= 1.4
        
        # Midday: Lighter, more uniform traffic
        midday_pattern = np.ones((self.grid_width, self.grid_height)) * 1.1
        
        # Night: Very light traffic
        night_pattern = np.ones((self.grid_width, self.grid_height)) * 0.9
        
        self.time_of_day_factors = {
            'morning_rush': morning_pattern,
            'evening_rush': evening_pattern,
            'midday': midday_pattern,
            'night': night_pattern
        }
    
    def get_time_period(self, sim_time_minutes: float) -> str:
        """Convert simulation time to traffic time period"""
        hour_of_day = (sim_time_minutes / 60) % 24
        
        if 7 <= hour_of_day < 9:
            return 'morning_rush'
        elif 16 <= hour_of_day < 19:
            return 'evening_rush'
        elif 9 <= hour_of_day < 16:
            return 'midday'
        else:
            return 'night'
    
    def add_traffic_zone(self, center_x: int, center_y: int, radius: int, 
                        severity: float, duration: float, zone_type: str = "incident"):
        """Add a temporary traffic disruption zone"""
        zone = TrafficZone(center_x, center_y, radius, severity, duration, zone_type)
        self.active_zones.append(zone)
    
    def remove_expired_zones(self, time_step: float):
        """Remove zones that have expired"""
        active_zones = []
        for zone in self.active_zones:
            zone.duration -= time_step
            if zone.duration > 0:
                active_zones.append(zone)
        self.active_zones = active_zones
    
    def get_traffic_factor(self, x: int, y: int, sim_time_minutes: float) -> float:
        """Get traffic congestion factor for a specific location and time"""
        
        # Base time-of-day factor
        time_period = self.get_time_period(sim_time_minutes)
        base_factor = self.time_of_day_factors[time_period][x, y]
        
        # Apply active traffic zones
        zone_factor = 1.0
        for zone in self.active_zones:
            distance = math.sqrt((x - zone.center_x)**2 + (y - zone.center_y)**2)
            if distance <= zone.radius:
                # Exponential decay of effect with distance
                effect_strength = math.exp(-distance / max(1, zone.radius / 2))
                zone_factor *= (1.0 + (zone.severity - 1.0) * effect_strength)
        
        return base_factor * zone_factor
    
    def get_traffic_condition(self, factor: float) -> TrafficCondition:
        """Convert traffic factor to condition enum"""
        if factor < 1.1:
            return TrafficCondition.FREE_FLOW
        elif factor < 1.5:
            return TrafficCondition.LIGHT
        elif factor < 2.0:
            return TrafficCondition.MODERATE
        elif factor < 3.0:
            return TrafficCondition.HEAVY
        else:
            return TrafficCondition.GRIDLOCK
    
    def update(self, time_step: float):
        """Update traffic model (remove expired zones, etc.)"""
        self.remove_expired_zones(time_step)
    
    def get_traffic_heatmap(self, sim_time_minutes: float) -> np.ndarray:
        """Get full grid traffic heatmap for visualization"""
        heatmap = np.zeros((self.grid_width, self.grid_height))
        
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                heatmap[x, y] = self.get_traffic_factor(x, y, sim_time_minutes)
        
        return heatmap
    
    def clear_all_zones(self):
        """Clear all active traffic zones"""
        self.active_zones.clear()
    
    def get_zone_info(self) -> List[Dict]:
        """Get information about active traffic zones"""
        return [
            {
                "center": (zone.center_x, zone.center_y),
                "radius": zone.radius,
                "severity": zone.severity,
                "duration_remaining": zone.duration,
                "type": zone.zone_type
            }
            for zone in self.active_zones
        ]

class WeatherModel:
    """Simple weather effects on traffic and ridership"""
    
    def __init__(self):
        self.current_condition = "clear"
        self.conditions = {
            "clear": {"traffic_factor": 1.0, "ridership_factor": 1.0},
            "rain": {"traffic_factor": 1.3, "ridership_factor": 1.4},
            "snow": {"traffic_factor": 2.0, "ridership_factor": 1.8},
            "storm": {"traffic_factor": 2.5, "ridership_factor": 2.2}
        }
    
    def set_condition(self, condition: str):
        """Set weather condition"""
        if condition in self.conditions:
            self.current_condition = condition
    
    def get_traffic_impact(self) -> float:
        """Get traffic slowdown factor due to weather"""
        return self.conditions[self.current_condition]["traffic_factor"]
    
    def get_ridership_impact(self) -> float:
        """Get ridership increase factor due to weather"""
        return self.conditions[self.current_condition]["ridership_factor"]
    
    def is_bad_weather(self) -> bool:
        """Check if current weather is bad"""
        return self.current_condition in ["rain", "snow", "storm"]

class CongestedRoadFinder:
    """Utility to find alternative routes around congested areas"""
    
    def __init__(self, city_grid, traffic_model):
        self.city_grid = city_grid
        self.traffic_model = traffic_model
    
    def find_least_congested_route(self, start: int, end: int, 
                                  current_time: float) -> List[int]:
        """Find route that avoids heavy traffic"""
        import networkx as nx
        
        # Create weighted graph based on current traffic
        temp_graph = nx.DiGraph()
        
        for (u, v), edge in self.city_grid.edges.items():
            if not edge.closed:
                # Get coordinates for traffic lookup
                u_pos = self.city_grid.id_to_node[u]
                v_pos = self.city_grid.id_to_node[v]
                
                # Average traffic factor for the edge
                traffic_u = self.traffic_model.get_traffic_factor(u_pos[0], u_pos[1], current_time)
                traffic_v = self.traffic_model.get_traffic_factor(v_pos[0], v_pos[1], current_time)
                avg_traffic = (traffic_u + traffic_v) / 2
                
                # Weight = base travel time × traffic factor
                weight = edge.base_time * avg_traffic
                temp_graph.add_edge(u, v, weight=weight)
        
        try:
            return nx.shortest_path(temp_graph, start, end, weight='weight')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Fallback to basic shortest path
            return self.city_grid.shortest_path(start, end)
    
    def get_congestion_level(self, path: List[int], current_time: float) -> float:
        """Calculate average congestion level along a path"""
        if len(path) < 2:
            return 1.0
        
        total_congestion = 0.0
        for i in range(len(path) - 1):
            node_pos = self.city_grid.id_to_node[path[i]]
            congestion = self.traffic_model.get_traffic_factor(
                node_pos[0], node_pos[1], current_time
            )
            total_congestion += congestion
        
        return total_congestion / (len(path) - 1)
