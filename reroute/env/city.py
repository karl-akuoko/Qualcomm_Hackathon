"""
City grid environment for bus routing simulation.
Models a 20x20 Manhattan-like grid with stops, roads, and traffic conditions.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random


@dataclass
class Stop:
    """Bus stop with position and queue information."""
    id: int
    x: int
    y: int
    queue_len: int = 0
    eta_list: List[float] = None
    
    def __post_init__(self):
        if self.eta_list is None:
            self.eta_list = []


@dataclass
class Edge:
    """Road edge between two grid points."""
    u: Tuple[int, int]
    v: Tuple[int, int]
    base_time: float  # base travel time in seconds
    factor: float = 1.0  # traffic factor (1.0 = normal, >1.0 = slower)
    closed: bool = False


class CityGrid:
    """20x20 Manhattan-like grid city with stops and road network."""
    
    def __init__(self, grid_size: int = 20, num_stops: int = 35, seed: int = 42):
        self.grid_size = grid_size
        self.num_stops = num_stops
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)
        
        # Initialize stops
        self.stops = self._create_stops()
        
        # Initialize road network
        self.edges = self._create_road_network()
        
        # Traffic conditions
        self.traffic_factors = {}
        
    def _create_stops(self) -> Dict[int, Stop]:
        """Create stops distributed across the grid."""
        stops = {}
        
        # Create stops with Manhattan-like distribution
        # More stops in center, fewer on edges
        stop_positions = []
        
        # Center area (high density)
        for x in range(6, 14):
            for y in range(6, 14):
                if random.random() < 0.4:  # 40% chance in center
                    stop_positions.append((x, y))
        
        # Outer areas (lower density)
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                if (x < 6 or x >= 14 or y < 6 or y >= 14):
                    if random.random() < 0.15:  # 15% chance in outer areas
                        stop_positions.append((x, y))
        
        # Ensure we have enough stops
        while len(stop_positions) < self.num_stops:
            x = random.randint(0, self.grid_size - 1)
            y = random.randint(0, self.grid_size - 1)
            if (x, y) not in stop_positions:
                stop_positions.append((x, y))
        
        # Create stop objects
        for i, (x, y) in enumerate(stop_positions[:self.num_stops]):
            stops[i] = Stop(id=i, x=x, y=y)
            
        return stops
    
    def _create_road_network(self) -> Dict[Tuple[Tuple[int, int], Tuple[int, int]], Edge]:
        """Create Manhattan-like road network."""
        edges = {}
        
        # Horizontal roads (avenues)
        for y in range(self.grid_size):
            for x in range(self.grid_size - 1):
                u = (x, y)
                v = (x + 1, y)
                base_time = 1.0 + random.uniform(0, 0.5)  # 1-1.5 seconds
                edges[(u, v)] = Edge(u=u, v=v, base_time=base_time)
                edges[(v, u)] = Edge(u=v, v=u, base_time=base_time)
        
        # Vertical roads (streets)
        for x in range(self.grid_size):
            for y in range(self.grid_size - 1):
                u = (x, y)
                v = (x, y + 1)
                base_time = 1.0 + random.uniform(0, 0.5)  # 1-1.5 seconds
                edges[(u, v)] = Edge(u=u, v=v, base_time=base_time)
                edges[(v, u)] = Edge(u=v, v=u, base_time=base_time)
        
        return edges
    
    def get_travel_time(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> float:
        """Get travel time between two positions."""
        edge = self.edges.get((from_pos, to_pos))
        if edge is None:
            # No direct connection, return Manhattan distance * base time
            dx = abs(to_pos[0] - from_pos[0])
            dy = abs(to_pos[1] - from_pos[1])
            return (dx + dy) * 2.0  # Penalty for indirect path
        
        if edge.closed:
            return float('inf')
        
        return edge.base_time * edge.factor
    
    def get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        neighbors = []
        x, y = pos
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < self.grid_size and 0 <= new_y < self.grid_size:
                neighbors.append((new_x, new_y))
        
        return neighbors
    
    def close_road(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]):
        """Close a road segment."""
        edge = self.edges.get((from_pos, to_pos))
        if edge:
            edge.closed = True
    
    def reopen_road(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]):
        """Reopen a road segment."""
        edge = self.edges.get((from_pos, to_pos))
        if edge:
            edge.closed = False
    
    def set_traffic_factor(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int], factor: float):
        """Set traffic factor for a road segment."""
        edge = self.edges.get((from_pos, to_pos))
        if edge:
            edge.factor = factor
    
    def reset_traffic(self):
        """Reset all traffic factors to normal."""
        for edge in self.edges.values():
            edge.factor = 1.0
            edge.closed = False
    
    def get_shortest_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get shortest path using A* algorithm."""
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        def get_path_cost(path):
            total_cost = 0
            for i in range(len(path) - 1):
                total_cost += self.get_travel_time(path[i], path[i + 1])
            return total_cost
        
        # A* search
        open_set = [(0, start)]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, goal)}
        
        while open_set:
            # Find minimum f_score
            min_idx = 0
            for i in range(len(open_set)):
                if open_set[i][0] < open_set[min_idx][0]:
                    min_idx = i
            
            current = open_set[min_idx][1]
            open_set.pop(min_idx)
            
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]
            
            for neighbor in self.get_neighbors(current):
                travel_time = self.get_travel_time(current, neighbor)
                if travel_time == float('inf'):
                    continue
                    
                tentative_g_score = g_score[current] + travel_time
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    
                    # Check if already in open_set
                    in_open_set = any(item[1] == neighbor for item in open_set)
                    if not in_open_set:
                        open_set.append((f_score[neighbor], neighbor))
        
        # No path found, return Manhattan path
        path = [start]
        current = start
        while current != goal:
            dx = goal[0] - current[0]
            dy = goal[1] - current[1]
            if dx != 0:
                current = (current[0] + (1 if dx > 0 else -1), current[1])
            else:
                current = (current[0], current[1] + (1 if dy > 0 else -1))
            path.append(current)
        return path
    
    def update_stop_queues(self, time_of_day: float):
        """Update stop queues based on time of day."""
        # Time-of-day arrival rates (Poisson-like)
        base_rate = 0.1  # base arrivals per second
        
        # Peak hours (morning 7-9, evening 5-7)
        hour = (time_of_day // 3600) % 24
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            multiplier = 2.0  # Peak hours
        elif 22 <= hour or hour <= 6:
            multiplier = 0.3  # Night hours
        else:
            multiplier = 1.0  # Normal hours
        
        # Add riders to stops
        for stop in self.stops.values():
            arrival_rate = base_rate * multiplier
            # Poisson process
            arrivals = np.random.poisson(arrival_rate)
            stop.queue_len += arrivals
