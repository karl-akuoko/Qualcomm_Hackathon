import numpy as np
import networkx as nx
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class EdgeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    SLOW = "slow"

@dataclass
class Edge:
    u: int
    v: int
    base_time: float
    factor: float = 1.0
    closed: bool = False
    
    @property
    def travel_time(self) -> float:
        if self.closed:
            return float('inf')
        return self.base_time * self.factor

@dataclass
class Stop:
    id: int
    x: int
    y: int
    queue_len: int = 0
    eta_list: List[float] = None
    
    def __post_init__(self):
        if self.eta_list is None:
            self.eta_list = []

class ManhattanGrid:
    """Manhattan-inspired 20x20 grid city with avenues (N-S) and streets (E-W)"""
    
    def __init__(self, width: int = 20, height: int = 20, num_stops: int = 32):
        self.width = width
        self.height = height
        self.num_stops = num_stops
        
        # Create grid graph
        self.graph = nx.grid_2d_graph(width, height, create_using=nx.DiGraph())
        
        # Convert to node IDs (flatten 2D coords to 1D)
        self.node_to_id = {(x, y): x * height + y for x, y in self.graph.nodes()}
        self.id_to_node = {v: k for k, v in self.node_to_id.items()}
        
        # Relabel graph with 1D IDs
        self.graph = nx.relabel_nodes(self.graph, self.node_to_id)
        
        # Add reverse edges for bidirectional streets
        edges_to_add = [(v, u) for u, v in self.graph.edges()]
        self.graph.add_edges_from(edges_to_add)
        
        # Initialize edges with Manhattan-style travel times
        self.edges: Dict[Tuple[int, int], Edge] = {}
        self._initialize_edges()
        
        # Place bus stops strategically (major intersections)
        self.stops: Dict[int, Stop] = {}
        self._place_stops()
        
    def _initialize_edges(self):
        """Initialize edges with Manhattan-style characteristics"""
        for u, v in self.graph.edges():
            u_pos = self.id_to_node[u]
            v_pos = self.id_to_node[v]
            
            # Base travel time depends on street type
            # Avenues (vertical, major N-S routes) are faster
            # Streets (horizontal, E-W routes) vary by location
            
            if abs(u_pos[0] - v_pos[0]) == 1:  # Horizontal (street)
                # Central streets (around Broadway equivalent) are slower
                center_y = self.height // 2
                distance_from_center = abs(u_pos[1] - center_y) / (self.height // 2)
                base_time = 2.0 + 1.0 * (1 - distance_from_center)  # 2-3 minutes
            else:  # Vertical (avenue)
                # Major avenues are faster, especially outer ones
                if u_pos[0] % 4 == 0:  # Major avenue every 4 blocks
                    base_time = 1.5  # Fast avenue
                else:
                    base_time = 2.0  # Regular avenue
            
            self.edges[(u, v)] = Edge(u, v, base_time)
    
    def _place_stops(self):
        """Place bus stops at strategic locations like Manhattan"""
        stop_locations = []
        
        # Major intersections (avenue intersections with key streets)
        major_avenues = [i for i in range(0, self.width, 4)]  # Every 4th avenue
        key_streets = [i for i in range(2, self.height, 6)]   # Every 6th street, offset
        
        for ave in major_avenues:
            for street in key_streets:
                if ave < self.width and street < self.height:
                    stop_locations.append((ave, street))
        
        # Add some intermediate stops on major avenues
        for ave in major_avenues[:3]:  # First 3 major avenues
            for street in range(1, self.height, 3):
                if street < self.height and (ave, street) not in stop_locations:
                    stop_locations.append((ave, street))
        
        # Limit to requested number of stops
        stop_locations = stop_locations[:self.num_stops]
        
        # Create stop objects
        for i, (x, y) in enumerate(stop_locations):
            node_id = self.node_to_id[(x, y)]
            self.stops[node_id] = Stop(id=node_id, x=x, y=y)
    
    def get_travel_time(self, u: int, v: int) -> float:
        """Get travel time between two nodes"""
        if (u, v) in self.edges:
            return self.edges[(u, v)].travel_time
        return float('inf')
    
    def close_edge(self, u: int, v: int):
        """Close an edge (road closure)"""
        if (u, v) in self.edges:
            self.edges[(u, v)].closed = True
        if (v, u) in self.edges:
            self.edges[(v, u)].closed = True
    
    def slow_edge(self, u: int, v: int, factor: float = 2.0):
        """Add traffic to an edge"""
        if (u, v) in self.edges:
            self.edges[(u, v)].factor = factor
        if (v, u) in self.edges:
            self.edges[(v, u)].factor = factor
    
    def reset_edge(self, u: int, v: int):
        """Reset edge to normal conditions"""
        if (u, v) in self.edges:
            self.edges[(u, v)].closed = False
            self.edges[(u, v)].factor = 1.0
        if (v, u) in self.edges:
            self.edges[(v, u)].closed = False
            self.edges[(v, u)].factor = 1.0
    
    def shortest_path(self, start: int, end: int) -> List[int]:
        """Find shortest path considering current edge conditions"""
        try:
            # Create temporary graph with current travel times
            temp_graph = nx.DiGraph()
            for (u, v), edge in self.edges.items():
                if not edge.closed:
                    temp_graph.add_edge(u, v, weight=edge.travel_time)
            
            return nx.shortest_path(temp_graph, start, end, weight='weight')
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def get_neighbors(self, node_id: int) -> List[int]:
        """Get neighboring nodes"""
        return list(self.graph.neighbors(node_id))
    
    def get_stop_ids(self) -> List[int]:
        """Get all stop IDs"""
        return list(self.stops.keys())
    
    def get_random_stop(self) -> int:
        """Get random stop ID"""
        return np.random.choice(list(self.stops.keys()))
    
    def distance_between_stops(self, stop1: int, stop2: int) -> float:
        """Manhattan distance between stops"""
        if stop1 not in self.stops or stop2 not in self.stops:
            return float('inf')
        
        s1 = self.stops[stop1]
        s2 = self.stops[stop2]
        return abs(s1.x - s2.x) + abs(s1.y - s2.y)
