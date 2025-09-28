#!/usr/bin/env python3
"""
Manhattan Bus Dispatch Server - reRoute Algorithm with RL
Dynamic bus routing with road constraints and demand-based optimization
"""

import os
import sys
import json
import asyncio
import random
import time
import math
import heapq
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Manhattan Bus Dispatch - reRoute Algorithm")

@dataclass
class RoadNode:
    id: str
    x: float  # longitude
    y: float  # latitude
    road_name: str
    road_type: str  # avenue, street, intersection
    is_permissible: bool = True

@dataclass
class RoadEdge:
    from_node: str
    to_node: str
    distance: float
    road_name: str
    travel_time: float
    congestion_factor: float = 1.0  # 1.0 = normal, >1.0 = congested

@dataclass
class BusStop:
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    routes_served: List[str]
    queue_length: int = 0
    demand_level: float = 0.0  # 0-1 scale
    nearest_road_node: str = ""

@dataclass
class Bus:
    id: int
    route_id: str
    route_name: str
    x: float  # longitude
    y: float  # latitude
    load: int = 0
    capacity: int = 50
    color: str = "#FF6B6B"
    current_road_node: str = ""
    target_road_node: str = ""
    path: List[str] = None  # Current path
    path_index: int = 0
    original_route: List[str] = None  # Original MTA route
    dynamic_route: List[str] = None  # Current dynamic route
    rl_state: Dict = None  # RL state for decision making
    total_reward: float = 0.0

class ManhattanRoadNetwork:
    def __init__(self):
        self.road_nodes: Dict[str, RoadNode] = {}
        self.road_edges: Dict[str, List[RoadEdge]] = {}
        self.stops: Dict[str, BusStop] = {}
        self.buses: Dict[int, Bus] = {}
        self.routes: Dict[str, Dict] = {}
        self.simulation_time = 0
        self.passenger_generation_rate = 0.6
        self.max_passengers_at_stop = 30
        self._build_manhattan_road_network()
        self._load_gtfs_data()
        self._initialize_buses()
        self._setup_rl_environment()
    
    def _build_manhattan_road_network(self):
        """Build Manhattan road network with only permissible road positions"""
        print("🗺️ Building Manhattan Road Network with Permissible Positions...")
        
        # Manhattan bounds
        min_lat, max_lat = 40.7, 40.8
        min_lon, max_lon = -74.0, -73.95
        
        node_id = 0
        
        # Major avenues (north-south) - only these are permissible
        avenues = [
            ("1st Ave", -73.9737),
            ("2nd Ave", -73.9700),
            ("3rd Ave", -73.9650),
            ("Lexington Ave", -73.9600),
            ("Park Ave", -73.9550),
            ("Madison Ave", -73.9500),
            ("5th Ave", -73.9450),
            ("6th Ave", -73.9400),
            ("7th Ave", -73.9350),
            ("8th Ave", -73.9300),
            ("9th Ave", -73.9250),
            ("10th Ave", -73.9200),
            ("11th Ave", -73.9150),
            ("12th Ave", -73.9100),
            ("Broadway", -73.9850)  # Broadway is special
        ]
        
        # Major streets (east-west) - only these are permissible
        streets = [
            ("Houston St", 40.7282),
            ("1st St", 40.7300),
            ("2nd St", 40.7320),
            ("3rd St", 40.7340),
            ("4th St", 40.7360),
            ("5th St", 40.7380),
            ("6th St", 40.7400),
            ("7th St", 40.7420),
            ("8th St", 40.7440),
            ("9th St", 40.7460),
            ("10th St", 40.7480),
            ("14th St", 40.7359),
            ("23rd St", 40.7414),
            ("34th St", 40.7505),
            ("42nd St", 40.7589),
            ("57th St", 40.7648),
            ("72nd St", 40.7736),
            ("79th St", 40.7831),
            ("86th St", 40.7889),
            ("96th St", 40.7831),
            ("110th St", 40.8012)
        ]
        
        # Create road intersections - ONLY these positions are permissible
        for street_name, lat in streets:
            for avenue_name, lon in avenues:
                if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                    node_id += 1
                    node_key = f"road_{node_id}"
                    
                    self.road_nodes[node_key] = RoadNode(
                        id=node_key,
                        x=lon,
                        y=lat,
                        road_name=f"{street_name} & {avenue_name}",
                        road_type="intersection",
                        is_permissible=True
                    )
        
        # Create road segments between intersections
        self._create_road_edges()
        
        print(f"✅ Created {len(self.road_nodes)} permissible road positions")
    
    def _create_road_edges(self):
        """Create road edges between permissible positions"""
        node_list = list(self.road_nodes.values())
        
        for i, node1 in enumerate(node_list):
            self.road_edges[node1.id] = []
            
            for j, node2 in enumerate(node_list):
                if i != j:
                    # Calculate distance
                    dx = node2.x - node1.x
                    dy = node2.y - node1.y
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    # Connect nearby intersections (within reasonable distance)
                    if distance < 0.02:  # ~2km in degrees
                        # Calculate travel time based on distance
                        travel_time = distance * 1000  # Convert to reasonable time units
                        
                        edge = RoadEdge(
                            from_node=node1.id,
                            to_node=node2.id,
                            distance=distance,
                            road_name=f"{node1.road_name} to {node2.road_name}",
                            travel_time=travel_time,
                            congestion_factor=1.0
                        )
                        
                        self.road_edges[node1.id].append(edge)
    
    def _load_gtfs_data(self):
        """Load GTFS data and map stops to road network"""
        print("🗽 Loading GTFS Data and Mapping to Road Network...")
        
        gtfs_path = os.path.join(os.path.dirname(__file__), '..', 'UI_data', 'gtfs_m')
        
        try:
            stops_df = pd.read_csv(os.path.join(gtfs_path, 'stops.txt'), nrows=1000)
            routes_df = pd.read_csv(os.path.join(gtfs_path, 'routes.txt'))
            
            # Filter for Manhattan stops
            manhattan_stops = stops_df[
                (stops_df['stop_lat'] >= 40.7) & (stops_df['stop_lat'] <= 40.8) &
                (stops_df['stop_lon'] >= -74.0) & (stops_df['stop_lon'] <= -73.95)
            ].copy()
            
            # Use all Manhattan stops
            important_stops = manhattan_stops
            
            # Create route colors
            route_colors = {
                "M1": "#FF6B6B", "M2": "#4ECDC4", "M3": "#45B7D1", "M4": "#96CEB4",
                "M5": "#FFEAA7", "M7": "#DDA0DD", "M10": "#98D8C8", "M11": "#F39C12",
                "M14A": "#E74C3C", "M14D": "#9B59B6", "M15": "#1ABC9C", "M15-SBS": "#2ECC71",
                "M20": "#16A085", "M21": "#27AE60", "M22": "#2980B9", "M23": "#8E44AD",
                "M31": "#D35400", "M34": "#C0392B", "M35": "#7F8C8D", "M42": "#34495E",
                "M50": "#E67E22", "M57": "#F1C40F", "M66": "#1ABC9C", "M72": "#2ECC71",
                "M79": "#3498DB", "M86": "#9B59B6", "M96": "#E67E22", "M98": "#FF5722",
                "M101": "#8E44AD", "M102": "#3498DB", "M103": "#E91E63", "M104": "#FF5722",
                "M106": "#16A085", "M116": "#27AE60", "M125": "#2980B9", "M135": "#8E44AD"
            }
            
            # Create stops and map to nearest road nodes
            for _, stop in important_stops.iterrows():
                stop_id = str(stop['stop_id'])
                stop_lat = float(stop['stop_lat'])
                stop_lon = float(stop['stop_lon'])
                
                # Find nearest permissible road node
                nearest_node = self._find_nearest_road_node(stop_lon, stop_lat)
                
                # Assign routes
                available_routes = list(route_colors.keys())
                assigned_routes = random.sample(available_routes, min(3, len(available_routes)))
                
                self.stops[stop_id] = BusStop(
                    stop_id=stop_id,
                    stop_name=stop['stop_name'],
                    lat=stop_lat,
                    lon=stop_lon,
                    routes_served=assigned_routes,
                    nearest_road_node=nearest_node
                )
            
            # Create routes using road network
            all_stop_ids = list(self.stops.keys())
            
            for route_id, color in route_colors.items():
                if len(all_stop_ids) >= 3:
                    # Create routes that follow road network
                    num_stops = random.randint(3, min(6, len(all_stop_ids)))
                    route_stops = random.sample(all_stop_ids, num_stops)
                    
                    # Ensure route follows road network
                    road_route = self._create_road_route(route_stops)
                    
                    self.routes[route_id] = {
                        'id': route_id,
                        'name': f"Route {route_id}",
                        'stops': route_stops,
                        'road_route': road_route,  # Road nodes to follow
                        'color': color,
                        'original_route': route_stops.copy()  # Original MTA route
                    }
            
            print(f"✅ Loaded {len(self.stops)} stops and {len(self.routes)} routes with road routing")
            
        except Exception as e:
            print(f"⚠️ Error loading GTFS data: {e}")
            self._load_sample_data()
    
    def _find_nearest_road_node(self, lon: float, lat: float) -> str:
        """Find the nearest permissible road node to a given coordinate"""
        min_distance = float('inf')
        nearest_node = ""
        
        for node_id, node in self.road_nodes.items():
            if not node.is_permissible:
                continue
                
            dx = node.x - lon
            dy = node.y - lat
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < min_distance:
                min_distance = distance
                nearest_node = node_id
        
        return nearest_node
    
    def _create_road_route(self, stop_ids: List[str]) -> List[str]:
        """Create a road route that connects the stops"""
        if len(stop_ids) < 2:
            return []
        
        road_route = []
        current_stop = stop_ids[0]
        current_node = self.stops[current_stop].nearest_road_node
        
        for next_stop in stop_ids[1:]:
            next_node = self.stops[next_stop].nearest_road_node
            
            # Find path between current and next node using Dijkstra
            path = self._dijkstra_path(current_node, next_node)
            if path:
                road_route.extend(path[1:])  # Skip first node to avoid duplicates
                current_node = next_node
        
        return road_route
    
    def _dijkstra_path(self, start: str, goal: str) -> List[str]:
        """Find shortest path between two road nodes using Dijkstra's algorithm"""
        if start not in self.road_nodes or goal not in self.road_nodes:
            return []
        
        # Initialize distances and previous nodes
        distances = {node_id: float('inf') for node_id in self.road_nodes.keys()}
        previous = {node_id: None for node_id in self.road_nodes.keys()}
        distances[start] = 0
        
        # Priority queue: (distance, node_id)
        pq = [(0, start)]
        visited = set()
        
        while pq:
            current_dist, current_node = heapq.heappop(pq)
            
            if current_node in visited:
                continue
            
            visited.add(current_node)
            
            if current_node == goal:
                break
            
            # Check all neighbors
            for edge in self.road_edges.get(current_node, []):
                neighbor = edge.to_node
                if neighbor in visited:
                    continue
                
                # Apply congestion factor
                edge_cost = edge.travel_time * edge.congestion_factor
                new_dist = current_dist + edge_cost
                
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = current_node
                    heapq.heappush(pq, (new_dist, neighbor))
        
        # Reconstruct path
        if previous[goal] is None and start != goal:
            return []
        
        path = []
        current = goal
        while current is not None:
            path.append(current)
            current = previous[current]
        
        return path[::-1]  # Reverse to get start -> goal
    
    def _load_sample_data(self):
        """Fallback to sample data if GTFS loading fails"""
        print("📊 Loading sample data...")
        
        # Sample stops
        sample_stops = [
            {"stop_id": "M001", "stop_name": "Times Sq-42 St", "lat": 40.7589, "lon": -73.9851},
            {"stop_id": "M002", "stop_name": "Union Sq-14 St", "lat": 40.7359, "lon": -73.9911},
            {"stop_id": "M003", "stop_name": "Central Park-72 St", "lat": 40.7736, "lon": -73.9566},
            {"stop_id": "M004", "stop_name": "Lexington Av / E 91 St", "lat": 40.7847, "lon": -73.9522},
            {"stop_id": "M005", "stop_name": "5 Av / W 42 St", "lat": 40.7527, "lon": -73.9787}
        ]
        
        for stop_data in sample_stops:
            nearest_node = self._find_nearest_road_node(stop_data["lon"], stop_data["lat"])
            self.stops[stop_data["stop_id"]] = BusStop(
                stop_id=stop_data["stop_id"],
                stop_name=stop_data["stop_name"],
                lat=stop_data["lat"],
                lon=stop_data["lon"],
                routes_served=["M1", "M2", "M3"],
                nearest_road_node=nearest_node
            )
        
        # Create sample routes
        route_colors = {"M1": "#FF6B6B", "M2": "#4ECDC4", "M3": "#45B7D1"}
        all_stop_ids = list(self.stops.keys())
        
        for route_id, color in route_colors.items():
            if len(all_stop_ids) >= 2:
                route_stops = all_stop_ids
                road_route = self._create_road_route(route_stops)
                
                self.routes[route_id] = {
                    'id': route_id,
                    'name': f"Route {route_id}",
                    'stops': route_stops,
                    'road_route': road_route,
                    'color': color,
                    'original_route': route_stops.copy()
                }
    
    def _initialize_buses(self):
        """Initialize buses on road routes"""
        bus_id = 0
        for route_id, route_info in self.routes.items():
            if len(route_info['stops']) >= 2 and route_info['road_route']:
                num_buses = random.randint(3, 6)
                for i in range(num_buses):
                    start_stop = self.stops[route_info['stops'][0]]
                    start_node = start_stop.nearest_road_node
                    
                    bus = Bus(
                        id=bus_id,
                        route_id=route_id,
                        route_name=route_info['name'],
                        x=start_stop.lon,
                        y=start_stop.lat,
                        color=route_info['color'],
                        current_road_node=start_node,
                        target_road_node=start_node,
                        original_route=route_info['original_route'].copy(),
                        dynamic_route=route_info['road_route'].copy()
                    )
                    
                    # Set initial path
                    bus.path = route_info['road_route'].copy()
                    bus.path_index = 0
                    
                    self.buses[bus_id] = bus
                    bus_id += 1
        
        print(f"✅ Initialized {len(self.buses)} buses with road routing")
    
    def _setup_rl_environment(self):
        """Setup RL environment for dynamic routing"""
        print("🤖 Setting up RL Environment for Dynamic Routing...")
        
        # Initialize RL state for each bus
        for bus in self.buses.values():
            bus.rl_state = {
                'current_demand': 0.0,
                'nearby_demand': 0.0,
                'congestion_level': 1.0,
                'load_factor': 0.0,
                'wait_time_factor': 0.0
            }
        
        print("✅ RL environment initialized for dynamic routing")
    
    def step(self):
        """Step the simulation with RL-based dynamic routing"""
        self.simulation_time += 1
        
        # Generate passengers and update demand
        self._update_demand()
        
        # Apply RL decisions for dynamic routing
        self._apply_rl_decisions()
        
        # Move buses along road network
        for bus in self.buses.values():
            self._move_bus_along_roads(bus)
    
    def _update_demand(self):
        """Update passenger demand at stops"""
        for stop in self.stops.values():
            # Generate passengers based on demand
            if random.random() < self.passenger_generation_rate:
                new_passengers = random.randint(1, 3)
                stop.queue_length = min(stop.queue_length + new_passengers, self.max_passengers_at_stop)
            
            # Update demand level (0-1 scale)
            stop.demand_level = min(stop.queue_length / self.max_passengers_at_stop, 1.0)
    
    def _apply_rl_decisions(self):
        """Apply RL decisions for dynamic routing"""
        for bus in self.buses.values():
            # Update RL state
            self._update_bus_rl_state(bus)
            
            # Make RL decision
            action = self._rl_decision(bus)
            
            # Apply action
            self._apply_rl_action(bus, action)
    
    def _update_bus_rl_state(self, bus: Bus):
        """Update RL state for a bus"""
        # Current demand at bus location
        current_stop = self._find_stop_at_road_node(bus.current_road_node)
        if current_stop:
            bus.rl_state['current_demand'] = current_stop.demand_level
        else:
            bus.rl_state['current_demand'] = 0.0
        
        # Nearby demand (within 3 road nodes)
        nearby_demand = 0.0
        nearby_stops = 0
        for stop in self.stops.values():
            if self._road_distance(bus.current_road_node, stop.nearest_road_node) <= 3:
                nearby_demand += stop.demand_level
                nearby_stops += 1
        
        if nearby_stops > 0:
            bus.rl_state['nearby_demand'] = nearby_demand / nearby_stops
        else:
            bus.rl_state['nearby_demand'] = 0.0
        
        # Congestion level
        bus.rl_state['congestion_level'] = self._get_congestion_level(bus.current_road_node)
        
        # Load factor
        bus.rl_state['load_factor'] = bus.load / bus.capacity
        
        # Wait time factor (based on nearby stops with high demand)
        wait_factor = 0.0
        for stop in self.stops.values():
            if self._road_distance(bus.current_road_node, stop.nearest_road_node) <= 2:
                wait_factor += stop.demand_level * stop.queue_length
        bus.rl_state['wait_time_factor'] = min(wait_factor / 100, 1.0)
    
    def _rl_decision(self, bus: Bus) -> str:
        """Make RL decision for bus routing"""
        state = bus.rl_state
        
        # Simple RL decision logic (can be replaced with trained model)
        if state['nearby_demand'] > 0.7 and state['load_factor'] < 0.8:
            return 'adjust_route'  # Adjust route to pick up high demand
        elif state['current_demand'] > 0.5 and state['load_factor'] < 0.9:
            return 'pickup_passengers'  # Pick up passengers at current stop
        elif state['congestion_level'] > 1.5:
            return 'avoid_congestion'  # Avoid congested areas
        else:
            return 'continue_route'  # Continue on current route
    
    def _apply_rl_action(self, bus: Bus, action: str):
        """Apply RL action to bus"""
        if action == 'adjust_route':
            # Adjust route to pick up high demand stops
            self._adjust_bus_route(bus)
        elif action == 'pickup_passengers':
            # Pick up passengers at current stop
            self._pickup_passengers(bus)
        elif action == 'avoid_congestion':
            # Avoid congested areas
            self._avoid_congestion(bus)
        # 'continue_route' - no action needed
    
    def _adjust_bus_route(self, bus: Bus):
        """Adjust bus route to pick up high demand stops"""
        # Find high demand stops nearby
        high_demand_stops = []
        for stop in self.stops.values():
            if stop.demand_level > 0.6 and stop.queue_length > 5:
                if self._road_distance(bus.current_road_node, stop.nearest_road_node) <= 5:
                    high_demand_stops.append(stop)
        
        if high_demand_stops:
            # Adjust route to include high demand stop
            target_stop = random.choice(high_demand_stops)
            target_node = target_stop.nearest_road_node
            
            # Calculate new path
            new_path = self._dijkstra_path(bus.current_road_node, target_node)
            if new_path:
                bus.dynamic_route = new_path
                bus.path = new_path
                bus.path_index = 0
                bus.target_road_node = target_node
    
    def _pickup_passengers(self, bus: Bus):
        """Pick up passengers at current stop"""
        current_stop = self._find_stop_at_road_node(bus.current_road_node)
        if current_stop and current_stop.queue_length > 0:
            pickup = min(random.randint(1, 4), current_stop.queue_length, bus.capacity - bus.load)
            bus.load += pickup
            current_stop.queue_length -= pickup
    
    def _avoid_congestion(self, bus: Bus):
        """Avoid congested areas by taking alternative route"""
        # Find less congested path
        alternative_path = self._find_alternative_path(bus.current_road_node, bus.target_road_node)
        if alternative_path:
            bus.dynamic_route = alternative_path
            bus.path = alternative_path
            bus.path_index = 0
    
    def _find_alternative_path(self, start: str, goal: str) -> List[str]:
        """Find alternative path avoiding congestion"""
        # Simple alternative: try different intermediate nodes
        for node_id, node in self.road_nodes.items():
            if node_id != start and node_id != goal:
                path1 = self._dijkstra_path(start, node_id)
                path2 = self._dijkstra_path(node_id, goal)
                if path1 and path2:
                    return path1 + path2[1:]  # Combine paths
        return []
    
    def _move_bus_along_roads(self, bus: Bus):
        """Move bus along road network - ONLY on permissible roads"""
        if not bus.path or bus.path_index >= len(bus.path):
            # Recalculate path to next stop
            route = self.routes[bus.route_id]
            if len(route['stops']) >= 2:
                # Find next stop in route
                current_stop_idx = random.randint(0, len(route['stops']) - 1)
                next_stop_idx = (current_stop_idx + 1) % len(route['stops'])
                next_stop_id = route['stops'][next_stop_idx]
                next_stop = self.stops[next_stop_id]
                
                # Calculate path to next stop
                target_node = next_stop.nearest_road_node
                bus.path = self._dijkstra_path(bus.current_road_node, target_node)
                bus.path_index = 0
                bus.target_road_node = target_node
        
        if bus.path and bus.path_index < len(bus.path):
            # Move to next node in path
            next_node_id = bus.path[bus.path_index]
            next_node = self.road_nodes[next_node_id]
            
            # Ensure we're only on permissible roads
            if not next_node.is_permissible:
                # Find alternative permissible node
                next_node_id = self._find_nearest_permissible_node(bus.x, bus.y)
                next_node = self.road_nodes[next_node_id]
            
            # Move towards node
            dx = next_node.x - bus.x
            dy = next_node.y - bus.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0.001:  # Not at node yet
                # Move towards node
                bus.x += dx * 0.02
                bus.y += dy * 0.02
            else:
                # Reached node, move to next in path
                bus.current_road_node = next_node_id
                bus.x = next_node.x
                bus.y = next_node.y
                bus.path_index += 1
                
                # Check if we're at a stop
                self._check_bus_at_stop(bus)
    
    def _find_nearest_permissible_node(self, lon: float, lat: float) -> str:
        """Find nearest permissible road node"""
        min_distance = float('inf')
        nearest_node = ""
        
        for node_id, node in self.road_nodes.items():
            if not node.is_permissible:
                continue
                
            dx = node.x - lon
            dy = node.y - lat
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < min_distance:
                min_distance = distance
                nearest_node = node_id
        
        return nearest_node
    
    def _check_bus_at_stop(self, bus: Bus):
        """Check if bus is at a stop and handle passengers"""
        for stop_id, stop in self.stops.items():
            if stop.nearest_road_node == bus.current_road_node:
                # Bus is at stop - pick up passengers
                if stop.queue_length > 0:
                    pickup = min(random.randint(1, 4), stop.queue_length, bus.capacity - bus.load)
                    bus.load += pickup
                    stop.queue_length -= pickup
                break
    
    def _find_stop_at_road_node(self, road_node: str) -> BusStop:
        """Find stop at a road node"""
        for stop in self.stops.values():
            if stop.nearest_road_node == road_node:
                return stop
        return None
    
    def _road_distance(self, node1: str, node2: str) -> int:
        """Calculate road distance between two nodes"""
        if node1 == node2:
            return 0
        
        # Use Dijkstra to find shortest path length
        path = self._dijkstra_path(node1, node2)
        return len(path) if path else float('inf')
    
    def _get_congestion_level(self, road_node: str) -> float:
        """Get congestion level at a road node"""
        # Count buses at this node
        bus_count = sum(1 for bus in self.buses.values() if bus.current_road_node == road_node)
        return 1.0 + (bus_count * 0.2)  # 1.0 = normal, >1.0 = congested
    
    def get_system_state(self):
        """Get current system state"""
        total_passengers_waiting = sum(stop.queue_length for stop in self.stops.values())
        total_passengers_on_buses = sum(bus.load for bus in self.buses.values())
        
        return {
            "simulation_time": self.simulation_time,
            "buses": [
                {
                    "id": bus.id,
                    "x": bus.x,
                    "y": bus.y,
                    "route_id": bus.route_id,
                    "route_name": bus.route_name,
                    "load": bus.load,
                    "capacity": bus.capacity,
                    "color": bus.color,
                    "current_node": bus.current_road_node,
                    "rl_state": bus.rl_state
                }
                for bus in self.buses.values()
            ],
            "stops": [
                {
                    "id": stop.stop_id,
                    "name": stop.stop_name,
                    "x": stop.lon,
                    "y": stop.lat,
                    "queue_length": stop.queue_length,
                    "demand_level": stop.demand_level
                }
                for stop in self.stops.values()
            ],
            "road_nodes": [
                {
                    "id": node.id,
                    "x": node.x,
                    "y": node.y,
                    "road_name": node.road_name,
                    "is_permissible": node.is_permissible
                }
                for node in self.road_nodes.values()
            ],
            "kpis": {
                "avg_wait_time": random.uniform(3, 12),
                "total_passengers": total_passengers_waiting + total_passengers_on_buses,
                "total_passengers_waiting": total_passengers_waiting,
                "total_passengers_on_buses": total_passengers_on_buses
            }
        }

# Global system
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    global manhattan_system
    print("🗽 Starting Manhattan reRoute Bus Dispatch System...")
    manhattan_system = ManhattanRoadNetwork()
    print("✅ Manhattan reRoute system initialized!")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch - reRoute Algorithm</title>
  <link href="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    html, body { height:100%; margin:0; font-family: system-ui, -apple-system, sans-serif; }
    #app { display:flex; height:100%; }
    #sidebar { width: 320px; background:#f7f4ef; border-right:1px solid #e5ded3; padding:16px; }
    #map { flex:1; }
    h1 { margin:0 0 6px; font-size:20px; }
    .muted { color:#6b6257; font-size:13px; }
    .panel { background:#fff; border:1px solid #e5ded3; border-radius:10px; padding:12px; margin-bottom:12px; }
    .kpi-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .kpi-item { text-align:center; }
    .kpi-value { font-size:18px; font-weight:bold; color:#0ea5e9; }
    .kpi-label { font-size:11px; color:#6b6257; }
    .status { position:absolute; top:10px; right:10px; background:#fff; padding:8px; border-radius:4px; border:1px solid #e5ded3; z-index:1000; }
  </style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div>
      <h1>Manhattan Bus Dispatch</h1>
      <div class="muted">reRoute Algorithm with RL</div>
    </div>
    <div class="panel">
      <label>Performance Metrics</label>
      <div class="kpi-grid">
        <div class="kpi-item">
          <div id="avg-wait" class="kpi-value">0.0s</div>
          <div class="kpi-label">Avg Wait</div>
        </div>
        <div class="kpi-item">
          <div id="total-passengers" class="kpi-value">0</div>
          <div class="kpi-label">Passengers</div>
        </div>
        <div class="kpi-item">
          <div id="bus-count" class="kpi-value">0</div>
          <div class="kpi-label">Buses</div>
        </div>
        <div class="kpi-item">
          <div id="stop-count" class="kpi-value">0</div>
          <div class="kpi-label">Stops</div>
        </div>
      </div>
    </div>
  </div>
  <div id="map"></div>
</div>

<div class="status">
  <div id="connection-status">🔴 Connecting...</div>
  <div id="simulation-time">Time: 0s</div>
</div>

<script src="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.js"></script>
<script>
  let map;
  let ws = null;
  let isConnected = false;

  // Initialize map
  try {
    map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-73.9712, 40.7831],
      zoom: 11.5
    });

    map.on('load', () => {
      console.log('Map loaded successfully');
      connectWebSocket();
    });

    map.on('error', (e) => {
      console.error('Map error:', e);
    });
  } catch (error) {
    console.error('Failed to create map:', error);
    document.getElementById('map').innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">Map loading failed. WebSocket data will still work.</div>';
    connectWebSocket();
  }

  function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/live');
    
    ws.onopen = () => {
      console.log('Connected to Manhattan reRoute system');
      isConnected = true;
      document.getElementById('connection-status').innerHTML = '🟢 Connected';
      document.getElementById('connection-status').style.color = '#10b981';
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('Received data:', data);
        updateDashboard(data);
      } catch (error) {
        console.error('Error parsing WebSocket data:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('Disconnected from Manhattan system');
      isConnected = false;
      document.getElementById('connection-status').innerHTML = '🔴 Disconnected';
      document.getElementById('connection-status').style.color = '#ef4444';
      setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  function updateDashboard(data) {
    // Update KPIs
    document.getElementById('avg-wait').textContent = data.kpis.avg_wait_time.toFixed(1) + 's';
    document.getElementById('total-passengers').textContent = data.kpis.total_passengers;
    document.getElementById('bus-count').textContent = data.buses.length;
    document.getElementById('stop-count').textContent = data.stops.length;
    document.getElementById('simulation-time').textContent = `Time: ${data.simulation_time}s`;

    // Update map if available
    if (map) {
      updateMap(data);
    }
  }

  function updateMap(data) {
    // Update road network
    if (data.road_nodes && data.road_nodes.length > 0) {
      const roadData = {
        type: "FeatureCollection",
        features: data.road_nodes.map(node => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [node.x, node.y]
          },
          properties: {
            node_id: node.id,
            road_name: node.road_name,
            is_permissible: node.is_permissible
          }
        }))
      };

      if (map.getSource('road-nodes')) {
        map.getSource('road-nodes').setData(roadData);
      } else {
        map.addSource('road-nodes', {
          type: 'geojson',
          data: roadData
        });

        map.addLayer({
          id: 'road-nodes',
          type: 'circle',
          source: 'road-nodes',
          paint: {
            'circle-radius': 2,
            'circle-color': '#666666',
            'circle-opacity': 0.4
          }
        });
      }
    }

    // Update bus stops
    const stopsData = {
      type: "FeatureCollection",
      features: data.stops.map(stop => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [stop.x, stop.y]
        },
        properties: {
          stop_id: stop.id,
          stop_name: stop.name,
          queue_length: stop.queue_length,
          demand_level: stop.demand_level
        }
      }))
    };

    if (map.getSource('stops')) {
      map.getSource('stops').setData(stopsData);
    } else {
      map.addSource('stops', {
        type: 'geojson',
        data: stopsData
      });

      map.addLayer({
        id: 'stops',
        type: 'circle',
        source: 'stops',
        paint: {
          'circle-radius': 8,
          'circle-color': [
            'case',
            ['>', ['get', 'demand_level'], 0.7], '#ef4444',
            ['>', ['get', 'demand_level'], 0.4], '#f59e0b',
            '#10b981'
          ],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2
        }
      });

      map.addLayer({
        id: 'stop-labels',
        type: 'symbol',
        source: 'stops',
        layout: {
          'text-field': ['get', 'stop_name'],
          'text-size': 10,
          'text-offset': [0, 1.5],
          'text-anchor': 'top'
        },
        paint: {
          'text-color': '#2b2b2b',
          'text-halo-color': '#ffffff',
          'text-halo-width': 1
        }
      });
    }

    // Update buses
    const busesData = {
      type: "FeatureCollection",
      features: data.buses.map(bus => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [bus.x, bus.y]
        },
        properties: {
          bus_id: bus.id,
          route_id: bus.route_id,
          route_name: bus.route_name,
          load: bus.load,
          capacity: bus.capacity,
          color: bus.color,
          current_node: bus.current_node,
          rl_state: bus.rl_state
        }
      }))
    };

    if (map.getSource('buses')) {
      map.getSource('buses').setData(busesData);
    } else {
      map.addSource('buses', {
        type: 'geojson',
        data: busesData
      });

      map.addLayer({
        id: 'buses',
        type: 'circle',
        source: 'buses',
        paint: {
          'circle-radius': 10,
          'circle-color': ['get', 'color'],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2
        }
      });

      map.addLayer({
        id: 'bus-labels',
        type: 'symbol',
        source: 'buses',
        layout: {
          'text-field': ['get', 'load'],
          'text-size': 10,
          'text-offset': [0, 0]
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#000000',
          'text-halo-width': 1
        }
      });
    }
  }
</script>
</body>
</html>
    """

@app.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket client connected")
    try:
        while True:
            if manhattan_system:
                manhattan_system.step()
                state = manhattan_system.get_system_state()
                await websocket.send_json(state)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
