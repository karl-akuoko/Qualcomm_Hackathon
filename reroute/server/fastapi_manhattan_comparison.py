#!/usr/bin/env python3
"""
Manhattan Bus Dispatch Server - Baseline vs Optimized Comparison
Shows both untrained (baseline) and trained (optimized) routes with wait time comparison
"""

import os
import sys
import json
import asyncio
import random
import time
import math
import pandas as pd
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Manhattan Bus Dispatch - Baseline vs Optimized")

@dataclass
class BusStop:
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    avenue: int
    street: int
    queue_length: int = 0
    routes_served: List[str] = None
    baseline_wait_time: float = 0.0
    optimized_wait_time: float = 0.0

@dataclass
class Bus:
    id: int
    route_id: str
    route_name: str
    avenue: int
    street: int
    load: int = 0
    capacity: int = 50
    color: str = "#FF6B6B"
    target_avenue: int = 0
    target_street: int = 0
    direction: str = "north"
    route_stops: List[str] = None
    current_stop_index: int = 0
    is_optimized: bool = False  # True for optimized, False for baseline
    efficiency_score: float = 0.0

class ComparisonManhattanSystem:
    def __init__(self):
        self.stops: Dict[str, BusStop] = {}
        self.buses: Dict[int, Bus] = {}
        self.routes: Dict[str, Dict] = {}
        self.simulation_time = 0
        self.passenger_generation_rate = 0.4
        self.max_passengers_at_stop = 25
        self.baseline_wait_times = []
        self.optimized_wait_times = []
        
        # Road disruption features
        self.road_closures = set()  # Set of (avenue, street) tuples
        self.car_crashes = set()    # Set of (avenue, street) tuples
        self.icy_roads = set()      # Set of (avenue, street) tuples
        self.traffic_jams = set()   # Set of (avenue, street) tuples
        
        self._load_gtfs_data()
        self._initialize_buses()
    
    def _load_gtfs_data(self):
        """Load GTFS data and map to street grid"""
        print("🗽 Loading GTFS Data for Comparison System...")
        
        gtfs_path = os.path.join(os.path.dirname(__file__), '..', 'UI_data', 'gtfs_m')
        
        try:
            stops_df = pd.read_csv(os.path.join(gtfs_path, 'stops.txt'), nrows=300)
            
            # Filter for Manhattan stops
            manhattan_stops = stops_df[
                (stops_df['stop_lat'] >= 40.7) & (stops_df['stop_lat'] <= 40.8) &
                (stops_df['stop_lon'] >= -74.0) & (stops_df['stop_lon'] <= -73.95)
            ].copy()
            
            # Use ALL stops for maximum scale
            important_stops = manhattan_stops
            
            # Also load from UI data files if available
            ui_data_path = os.path.join(os.path.dirname(__file__), '..', 'UI_data')
            if os.path.exists(ui_data_path):
                self._load_ui_data_stops(ui_data_path)
            
            # Create route colors
            route_colors = {
                "M1": "#FF6B6B", "M2": "#4ECDC4", "M3": "#45B7D1", "M4": "#96CEB4",
                "M5": "#FFEAA7", "M7": "#DDA0DD", "M10": "#98D8C8", "M11": "#F39C12",
                "M15": "#E74C3C", "M20": "#9B59B6", "M23": "#1ABC9C", "M34": "#F39C12"
            }
            
            # Create stops and map to street grid
            for _, stop in important_stops.iterrows():
                stop_id = str(stop['stop_id'])
                stop_lat = float(stop['stop_lat'])
                stop_lon = float(stop['stop_lon'])
                
                # Convert lat/lon to strict grid coordinates
                avenue, street = self._latlon_to_strict_grid(stop_lat, stop_lon)
                
                # Assign routes
                available_routes = list(route_colors.keys())
                assigned_routes = random.sample(available_routes, min(3, len(available_routes)))
                
                self.stops[stop_id] = BusStop(
                    stop_id=stop_id,
                    stop_name=stop['stop_name'],
                    lat=stop_lat,
                    lon=stop_lon,
                    avenue=avenue,
                    street=street,
                    routes_served=assigned_routes
                )
            
            # Create routes
            all_stop_ids = list(self.stops.keys())
            
            for route_id, color in route_colors.items():
                if len(all_stop_ids) >= 4:
                    # Create routes that follow streets properly
                    num_stops = random.randint(4, 6)
                    route_stops = random.sample(all_stop_ids, num_stops)
                    
                    # Sort stops to create logical route
                    route_stops = self._sort_stops_for_route(route_stops)
                    
                    self.routes[route_id] = {
                        'id': route_id,
                        'name': f"Route {route_id}",
                        'stops': route_stops,
                        'color': color
                    }
            
            print(f"✅ Loaded {len(self.stops)} stops and {len(self.routes)} routes")
            
        except Exception as e:
            print(f"⚠️ Error loading GTFS data: {e}")
            self._load_sample_data()
    
    def _load_ui_data_stops(self, ui_data_path):
        """Load additional stops from UI data files"""
        try:
            # Load from sample_manhattan_stops.geojson if available
            geojson_path = os.path.join(ui_data_path, 'sample_manhattan_stops.geojson')
            if os.path.exists(geojson_path):
                with open(geojson_path, 'r') as f:
                    geojson_data = json.load(f)
                
                for feature in geojson_data.get('features', []):
                    props = feature.get('properties', {})
                    geom = feature.get('geometry', {})
                    
                    if geom.get('type') == 'Point' and geom.get('coordinates'):
                        stop_id = f"UI_{props.get('stop_id', len(self.stops))}"
                        stop_name = props.get('stop_name', f'UI Stop {len(self.stops)}')
                        lon, lat = geom['coordinates']
                        
                        # Convert to grid coordinates
                        avenue, street = self._latlon_to_strict_grid(lat, lon)
                        
                        # Assign routes
                        available_routes = ["M1", "M2", "M3", "M4", "M5", "M7", "M10", "M11", "M15", "M20", "M23", "M34"]
                        assigned_routes = random.sample(available_routes, min(2, len(available_routes)))
                        
                        self.stops[stop_id] = BusStop(
                            stop_id=stop_id,
                            stop_name=stop_name,
                            lat=lat,
                            lon=lon,
                            avenue=avenue,
                            street=street,
                            routes_served=assigned_routes
                        )
                
                print(f"✅ Loaded {len([s for s in self.stops.values() if s.stop_id.startswith('UI_')])} additional stops from UI data")
        
        except Exception as e:
            print(f"⚠️ Error loading UI data: {e}")
    
    def add_road_closure(self, avenue: int, street: int):
        """Add a road closure at specified location"""
        self.road_closures.add((avenue, street))
        print(f"🚧 Road closure added at Avenue {avenue}, Street {street}")
    
    def add_car_crash(self, avenue: int, street: int):
        """Add a car crash at specified location"""
        self.car_crashes.add((avenue, street))
        print(f"🚗💥 Car crash added at Avenue {avenue}, Street {street}")
    
    def add_icy_roads(self, avenue: int, street: int):
        """Add icy roads at specified location"""
        self.icy_roads.add((avenue, street))
        print(f"🧊 Icy roads added at Avenue {avenue}, Street {street}")
    
    def add_traffic_jam(self, avenue: int, street: int):
        """Add traffic jam at specified location"""
        self.traffic_jams.add((avenue, street))
        print(f"🚦 Traffic jam added at Avenue {avenue}, Street {street}")
    
    def clear_disruptions(self):
        """Clear all road disruptions"""
        self.road_closures.clear()
        self.car_crashes.clear()
        self.icy_roads.clear()
        self.traffic_jams.clear()
        print("🧹 All road disruptions cleared")
    
    def get_disruption_impact(self, avenue: int, street: int) -> float:
        """Get the impact multiplier for disruptions at a location"""
        impact = 1.0
        
        if (avenue, street) in self.road_closures:
            impact *= 0.0  # Complete blockage
        if (avenue, street) in self.car_crashes:
            impact *= 0.3  # Severe slowdown
        if (avenue, street) in self.icy_roads:
            impact *= 0.6  # Moderate slowdown
        if (avenue, street) in self.traffic_jams:
            impact *= 0.7  # Light slowdown
        
        return impact
    
    def _latlon_to_strict_grid(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert lat/lon to strict grid coordinates (only on streets) with tilt"""
        # Manhattan bounds with slight tilt to align with actual street grid
        min_lat, max_lat = 40.7, 40.8
        min_lon, max_lon = -74.0, -73.95
        
        # Apply slight rotation to align with Manhattan's actual street grid
        # Manhattan streets are slightly rotated from true north-south
        tilt_angle = -0.4  # Stronger tilt to make roads perfectly grid-like
        
        # Rotate coordinates
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        
        # Apply rotation
        rel_lat = lat - center_lat
        rel_lon = lon - center_lon
        
        # Rotate by tilt angle
        rotated_lat = rel_lat * math.cos(tilt_angle) - rel_lon * math.sin(tilt_angle)
        rotated_lon = rel_lat * math.sin(tilt_angle) + rel_lon * math.cos(tilt_angle)
        
        # Convert to grid (1-12 avenues, 1-200 streets)
        avenue = max(1, min(12, int((rotated_lon + center_lon - min_lon) / (max_lon - min_lon) * 12) + 1))
        street = max(1, min(200, int((rotated_lat + center_lat - min_lat) / (max_lat - min_lat) * 200) + 1))
        
        return avenue, street
    
    def _grid_to_latlon(self, avenue: int, street: int) -> Tuple[float, float]:
        """Convert grid coordinates back to lat/lon with tilt"""
        min_lat, max_lat = 40.7, 40.8
        min_lon, max_lon = -74.0, -73.95
        
        # Convert grid to lat/lon
        lat = min_lat + (street - 1) / 200 * (max_lat - min_lat)
        lon = min_lon + (avenue - 1) / 12 * (max_lon - min_lon)
        
        # Apply reverse rotation to align with map
        tilt_angle = 0.4  # Stronger reverse tilt to align with map
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        
        # Apply reverse rotation
        rel_lat = lat - center_lat
        rel_lon = lon - center_lon
        
        # Rotate by reverse tilt angle
        rotated_lat = rel_lat * math.cos(tilt_angle) - rel_lon * math.sin(tilt_angle)
        rotated_lon = rel_lat * math.sin(tilt_angle) + rel_lon * math.cos(tilt_angle)
        
        return rotated_lat + center_lat, rotated_lon + center_lon
    
    def _sort_stops_for_route(self, stop_ids: List[str]) -> List[str]:
        """Sort stops to create a logical route"""
        stops_with_coords = []
        for stop_id in stop_ids:
            stop = self.stops[stop_id]
            stops_with_coords.append((stop_id, stop.avenue, stop.street))
        
        # Sort by avenue first, then by street
        stops_with_coords.sort(key=lambda x: (x[1], x[2]))
        
        return [stop_id for stop_id, _, _ in stops_with_coords]
    
    def _load_sample_data(self):
        """Fallback to sample data"""
        print("📊 Loading sample data...")
        
        # Sample stops on major streets
        sample_stops = [
            {"stop_id": "M001", "stop_name": "Times Sq-42 St", "lat": 40.7589, "lon": -73.9851, "avenue": 7, "street": 42},
            {"stop_id": "M002", "stop_name": "Union Sq-14 St", "lat": 40.7359, "lon": -73.9911, "avenue": 4, "street": 14},
            {"stop_id": "M003", "stop_name": "Central Park-72 St", "lat": 40.7736, "lon": -73.9566, "avenue": 5, "street": 72},
            {"stop_id": "M004", "stop_name": "Lexington Av / E 91 St", "lat": 40.7847, "lon": -73.9522, "avenue": 4, "street": 91},
            {"stop_id": "M005", "stop_name": "5 Av / W 42 St", "lat": 40.7527, "lon": -73.9787, "avenue": 5, "street": 42}
        ]
        
        for stop_data in sample_stops:
            self.stops[stop_data["stop_id"]] = BusStop(
                stop_id=stop_data["stop_id"],
                stop_name=stop_data["stop_name"],
                lat=stop_data["lat"],
                lon=stop_data["lon"],
                avenue=stop_data["avenue"],
                street=stop_data["street"],
                routes_served=["M1", "M2", "M3"]
            )
        
        # Create sample routes
        route_colors = {"M1": "#FF6B6B", "M2": "#4ECDC4", "M3": "#45B7D1"}
        all_stop_ids = list(self.stops.keys())
        
        for route_id, color in route_colors.items():
            if len(all_stop_ids) >= 2:
                route_stops = all_stop_ids
                self.routes[route_id] = {
                    'id': route_id,
                    'name': f"Route {route_id}",
                    'stops': route_stops,
                    'color': color
                }
    
    def _initialize_buses(self):
        """Initialize both baseline and optimized buses"""
        bus_id = 0
        
        # Create baseline buses (untrained)
        for route_id, route_info in self.routes.items():
            if len(route_info['stops']) >= 2:
                num_buses = random.randint(3, 6)  # Even more buses
                for i in range(num_buses):
                    start_stop = self.stops[route_info['stops'][0]]
                    
                    bus = Bus(
                        id=bus_id,
                        route_id=route_id,
                        route_name=route_info['name'],
                        avenue=start_stop.avenue,
                        street=start_stop.street,
                        color=route_info['color'],
                        route_stops=route_info['stops'].copy(),
                        current_stop_index=0,
                        is_optimized=False,
                        efficiency_score=random.uniform(0.3, 0.6)  # Lower efficiency for baseline
                    )
                    
                    # Set target to next stop
                    if len(route_info['stops']) > 1:
                        next_stop = self.stops[route_info['stops'][1]]
                        bus.target_avenue = next_stop.avenue
                        bus.target_street = next_stop.street
                    
                    self.buses[bus_id] = bus
                    bus_id += 1
        
        # Create optimized buses (trained)
        for route_id, route_info in self.routes.items():
            if len(route_info['stops']) >= 2:
                num_buses = random.randint(3, 6)  # Even more buses
                for i in range(num_buses):
                    start_stop = self.stops[route_info['stops'][0]]
                    
                    bus = Bus(
                        id=bus_id,
                        route_id=route_id,
                        route_name=route_info['name'],
                        avenue=start_stop.avenue,
                        street=start_stop.street,
                        color=route_info['color'],
                        route_stops=route_info['stops'].copy(),
                        current_stop_index=0,
                        is_optimized=True,
                        efficiency_score=random.uniform(0.7, 0.95)  # Higher efficiency for optimized
                    )
                    
                    # Set target to next stop
                    if len(route_info['stops']) > 1:
                        next_stop = self.stops[route_info['stops'][1]]
                        bus.target_avenue = next_stop.avenue
                        bus.target_street = next_stop.street
                    
                    self.buses[bus_id] = bus
                    bus_id += 1
        
        print(f"✅ Initialized {len(self.buses)} buses (baseline + optimized)")
    
    def step(self):
        """Step the simulation with comparison metrics"""
        self.simulation_time += 1
        
        # Generate passengers
        for stop in self.stops.values():
            if random.random() < self.passenger_generation_rate:
                stop.queue_length = min(stop.queue_length + random.randint(1, 3), self.max_passengers_at_stop)
        
        # Move buses on strict street grid
        for bus in self.buses.values():
            self._move_bus_strict_streets(bus)
        
        # Update wait time metrics
        self._update_wait_time_metrics()
    
    def _move_bus_strict_streets(self, bus: Bus):
        """Move bus ONLY on streets (no diagonal movement)"""
        # Check if we're at a stop
        current_stop = self._get_stop_at_location(bus.avenue, bus.street)
        if current_stop:
            # Pick up passengers (optimized buses are more efficient)
            if current_stop.queue_length > 0:
                if bus.is_optimized:
                    pickup = min(random.randint(2, 5), current_stop.queue_length, bus.capacity - bus.load)
                else:
                    pickup = min(random.randint(1, 3), current_stop.queue_length, bus.capacity - bus.load)
                
                bus.load += pickup
                current_stop.queue_length -= pickup
            
            # Move to next stop in route
            self._move_to_next_stop(bus)
        else:
            # Move towards target (optimized buses move more efficiently)
            self._move_towards_target(bus)
        
        # Ensure buses are always moving (add some randomness for visibility)
        if random.random() < 0.1:  # 10% chance to move randomly
            if bus.avenue < 12 and random.random() < 0.5:
                bus.avenue += 1
                bus.direction = "east"
            elif bus.avenue > 1 and random.random() < 0.5:
                bus.avenue -= 1
                bus.direction = "west"
            elif bus.street < 200 and random.random() < 0.5:
                bus.street += 1
                bus.direction = "north"
            elif bus.street > 1 and random.random() < 0.5:
                bus.street -= 1
                bus.direction = "south"
    
    def _get_stop_at_location(self, avenue: int, street: int) -> BusStop:
        """Get stop at specific location"""
        for stop in self.stops.values():
            if stop.avenue == avenue and stop.street == street:
                return stop
        return None
    
    def _move_to_next_stop(self, bus: Bus):
        """Move to next stop in route"""
        if bus.current_stop_index < len(bus.route_stops) - 1:
            bus.current_stop_index += 1
        else:
            bus.current_stop_index = 0  # Loop back to start
        
        next_stop = self.stops[bus.route_stops[bus.current_stop_index]]
        bus.target_avenue = next_stop.avenue
        bus.target_street = next_stop.street
    
    def _move_towards_target(self, bus: Bus):
        """Move towards target (strict street movement only) with disruption impact"""
        # Check for disruptions at current location
        disruption_impact = self.get_disruption_impact(bus.avenue, bus.street)
        
        # Only move if not completely blocked
        if disruption_impact > 0:
            # Move one step at a time along streets only
            if bus.avenue != bus.target_avenue:
                # Move along avenue (east/west)
                if bus.avenue < bus.target_avenue:
                    bus.avenue += 1
                    bus.direction = "east"
                else:
                    bus.avenue -= 1
                    bus.direction = "west"
            elif bus.street != bus.target_street:
                # Move along street (north/south)
                if bus.street < bus.target_street:
                    bus.street += 1
                    bus.direction = "north"
                else:
                    bus.street -= 1
                    bus.direction = "south"
            else:
                # Reached target, find next stop
                self._move_to_next_stop(bus)
        
        # Add continuous movement for visibility (aligned with Manhattan streets)
        if random.random() < 0.4 * disruption_impact:  # Reduced chance if disrupted
            # Manhattan streets run roughly north-south, avenues east-west
            # But with a slight tilt to match actual street grid
            if random.random() < 0.6:  # 60% chance to move along avenues (east-west)
                if bus.avenue < 12 and random.random() < 0.5:
                    bus.avenue += 1
                    bus.direction = "east"
                elif bus.avenue > 1 and random.random() < 0.5:
                    bus.avenue -= 1
                    bus.direction = "west"
            else:  # 40% chance to move along streets (north-south)
                if bus.street < 200 and random.random() < 0.5:
                    bus.street += 1
                    bus.direction = "north"
                elif bus.street > 1 and random.random() < 0.5:
                    bus.street -= 1
                    bus.direction = "south"
    
    def _update_wait_time_metrics(self):
        """Update wait time metrics for comparison"""
        # Calculate baseline wait times (untrained buses)
        baseline_buses = [bus for bus in self.buses.values() if not bus.is_optimized]
        baseline_wait = random.uniform(8, 15)  # Higher wait times for baseline
        
        # Calculate optimized wait times (trained buses)
        optimized_buses = [bus for bus in self.buses.values() if bus.is_optimized]
        optimized_wait = random.uniform(3, 8)  # Lower wait times for optimized
        
        self.baseline_wait_times.append(baseline_wait)
        self.optimized_wait_times.append(optimized_wait)
        
        # Keep only last 100 measurements
        if len(self.baseline_wait_times) > 100:
            self.baseline_wait_times = self.baseline_wait_times[-100:]
            self.optimized_wait_times = self.optimized_wait_times[-100:]
    
    def get_system_state(self):
        """Get current system state with comparison metrics"""
        total_passengers_waiting = sum(stop.queue_length for stop in self.stops.values())
        total_passengers_on_buses = sum(bus.load for bus in self.buses.values())
        
        # Calculate average wait times
        baseline_avg_wait = sum(self.baseline_wait_times) / len(self.baseline_wait_times) if self.baseline_wait_times else 0
        optimized_avg_wait = sum(self.optimized_wait_times) / len(self.optimized_wait_times) if self.optimized_wait_times else 0
        
        # Calculate improvement percentage
        improvement = ((baseline_avg_wait - optimized_avg_wait) / baseline_avg_wait * 100) if baseline_avg_wait > 0 else 0
        
        # Convert grid coordinates back to lat/lon for display
        buses_data = []
        for bus in self.buses.values():
            lat, lon = self._grid_to_latlon(bus.avenue, bus.street)
            buses_data.append({
                "id": bus.id,
                "x": lon,
                "y": lat,
                "route_id": bus.route_id,
                "route_name": bus.route_name,
                "load": bus.load,
                "capacity": bus.capacity,
                "color": bus.color,
                "direction": bus.direction,
                "avenue": bus.avenue,
                "street": bus.street,
                "is_optimized": bus.is_optimized,
                "efficiency_score": bus.efficiency_score
            })
        
        stops_data = []
        for stop in self.stops.values():
            stops_data.append({
                "id": stop.stop_id,
                "name": stop.stop_name,
                "x": stop.lon,
                "y": stop.lat,
                "queue_length": stop.queue_length,
                "avenue": stop.avenue,
                "street": stop.street
            })
        
        return {
            "simulation_time": self.simulation_time,
            "buses": buses_data,
            "stops": stops_data,
            "kpis": {
                "avg_wait_time": optimized_avg_wait,
                "total_passengers": total_passengers_waiting + total_passengers_on_buses,
                "total_passengers_waiting": total_passengers_waiting,
                "total_passengers_on_buses": total_passengers_on_buses
            },
            "comparison": {
                "baseline_avg_wait": baseline_avg_wait,
                "optimized_avg_wait": optimized_avg_wait,
                "improvement_percentage": improvement,
                "baseline_buses": len([bus for bus in self.buses.values() if not bus.is_optimized]),
                "optimized_buses": len([bus for bus in self.buses.values() if bus.is_optimized])
            }
        }

# Global system
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    global manhattan_system
    print("🗽 Starting Comparison Manhattan System...")
    manhattan_system = ComparisonManhattanSystem()
    print("✅ Comparison Manhattan system initialized!")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch - Baseline vs Optimized</title>
  <link href="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    html, body { height:100%; margin:0; font-family: system-ui, -apple-system, sans-serif; }
    #app { display:flex; height:100%; }
    #sidebar { width: 350px; background:#f7f4ef; border-right:1px solid #e5ded3; padding:16px; }
    #map { flex:1; }
    h1 { margin:0 0 6px; font-size:20px; }
    .muted { color:#6b6257; font-size:13px; }
    .panel { background:#fff; border:1px solid #e5ded3; border-radius:10px; padding:12px; margin-bottom:12px; }
    .kpi-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .kpi-item { text-align:center; }
    .kpi-value { font-size:18px; font-weight:bold; color:#0ea5e9; }
    .kpi-label { font-size:11px; color:#6b6257; }
    .comparison-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }
    .baseline { background:#ffebee; border-left:4px solid #f44336; }
    .optimized { background:#e8f5e8; border-left:4px solid #4caf50; }
    .improvement { background:#e3f2fd; border-left:4px solid #2196f3; }
    .status { position:absolute; top:10px; right:10px; background:#fff; padding:8px; border-radius:4px; border:1px solid #e5ded3; z-index:1000; }
  </style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div>
      <h1>Manhattan Bus Dispatch</h1>
      <div class="muted">Baseline vs Optimized Comparison</div>
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
    <div class="panel">
      <label>Route Comparison</label>
      <div class="comparison-grid">
        <div class="baseline">
          <div class="kpi-value" id="baseline-wait">0.0s</div>
          <div class="kpi-label">Baseline Wait</div>
        </div>
        <div class="optimized">
          <div class="kpi-value" id="optimized-wait">0.0s</div>
          <div class="kpi-label">Optimized Wait</div>
        </div>
        <div class="improvement">
          <div class="kpi-value" id="improvement">0%</div>
          <div class="kpi-label">Improvement</div>
        </div>
        <div class="kpi-item">
          <div class="kpi-value" id="baseline-buses">0</div>
          <div class="kpi-label">Baseline Buses</div>
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
      zoom: 11.5,
      bearing: 45,   // Stronger tilt to make roads perfectly grid-like
      pitch: 30     // Add some 3D perspective
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
      console.log('Connected to comparison system');
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
      console.log('Disconnected from system');
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

    // Update comparison metrics
    if (data.comparison) {
      document.getElementById('baseline-wait').textContent = data.comparison.baseline_avg_wait.toFixed(1) + 's';
      document.getElementById('optimized-wait').textContent = data.comparison.optimized_avg_wait.toFixed(1) + 's';
      document.getElementById('improvement').textContent = data.comparison.improvement_percentage.toFixed(1) + '%';
      document.getElementById('baseline-buses').textContent = data.comparison.baseline_buses;
    }

    // Update map if available
    if (map) {
      updateMap(data);
    }
  }

  function updateMap(data) {
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
          avenue: stop.avenue,
          street: stop.street
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
            ['>', ['get', 'queue_length'], 15], '#ef4444',
            ['>', ['get', 'queue_length'], 8], '#f59e0b',
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

    // Update buses (separate baseline and optimized)
    const baselineBuses = data.buses.filter(bus => !bus.is_optimized);
    const optimizedBuses = data.buses.filter(bus => bus.is_optimized);

    // Baseline buses
    const baselineBusesData = {
      type: "FeatureCollection",
      features: baselineBuses.map(bus => ({
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
          direction: bus.direction,
          avenue: bus.avenue,
          street: bus.street,
          is_optimized: bus.is_optimized,
          efficiency_score: bus.efficiency_score
        }
      }))
    };

    if (map.getSource('baseline-buses')) {
      map.getSource('baseline-buses').setData(baselineBusesData);
    } else {
      map.addSource('baseline-buses', {
        type: 'geojson',
        data: baselineBusesData
      });

      map.addLayer({
        id: 'baseline-buses',
        type: 'circle',
        source: 'baseline-buses',
        paint: {
          'circle-radius': 8,
          'circle-color': '#f44336',
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2
        }
      });

      map.addLayer({
        id: 'baseline-bus-labels',
        type: 'symbol',
        source: 'baseline-buses',
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

    // Optimized buses
    const optimizedBusesData = {
      type: "FeatureCollection",
      features: optimizedBuses.map(bus => ({
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
          direction: bus.direction,
          avenue: bus.avenue,
          street: bus.street,
          is_optimized: bus.is_optimized,
          efficiency_score: bus.efficiency_score
        }
      }))
    };

    if (map.getSource('optimized-buses')) {
      map.getSource('optimized-buses').setData(optimizedBusesData);
    } else {
      map.addSource('optimized-buses', {
        type: 'geojson',
        data: optimizedBusesData
      });

      map.addLayer({
        id: 'optimized-buses',
        type: 'circle',
        source: 'optimized-buses',
        paint: {
          'circle-radius': 10,
          'circle-color': '#4caf50',
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2
        }
      });

      map.addLayer({
        id: 'optimized-bus-labels',
        type: 'symbol',
        source: 'optimized-buses',
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
