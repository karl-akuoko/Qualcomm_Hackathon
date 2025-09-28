#!/usr/bin/env python3
"""
Manhattan Bus Dispatch Server - Simple Street Grid
Buses only move on actual Manhattan streets (avenues and streets)
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

app = FastAPI(title="Manhattan Bus Dispatch - Simple Streets")

@dataclass
class StreetGrid:
    x: int  # Avenue number (1-12)
    y: int  # Street number (1-200)
    is_street: bool = True

@dataclass
class BusStop:
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    avenue: int  # Which avenue (1-12)
    street: int  # Which street (1-200)
    queue_length: int = 0
    routes_served: List[str] = None

@dataclass
class Bus:
    id: int
    route_id: str
    route_name: str
    avenue: int  # Current avenue
    street: int  # Current street
    load: int = 0
    capacity: int = 50
    color: str = "#FF6B6B"
    target_avenue: int = 0
    target_street: int = 0
    direction: str = "north"  # north, south, east, west

class SimpleManhattanSystem:
    def __init__(self):
        self.stops: Dict[str, BusStop] = {}
        self.buses: Dict[int, Bus] = {}
        self.routes: Dict[str, Dict] = {}
        self.simulation_time = 0
        self.passenger_generation_rate = 0.3
        self.max_passengers_at_stop = 20
        self._load_gtfs_data()
        self._initialize_buses()
    
    def _load_gtfs_data(self):
        """Load GTFS data and map to simple street grid"""
        print("🗽 Loading GTFS Data for Simple Street System...")
        
        gtfs_path = os.path.join(os.path.dirname(__file__), '..', 'UI_data', 'gtfs_m')
        
        try:
            stops_df = pd.read_csv(os.path.join(gtfs_path, 'stops.txt'), nrows=500)
            
            # Filter for Manhattan stops
            manhattan_stops = stops_df[
                (stops_df['stop_lat'] >= 40.7) & (stops_df['stop_lat'] <= 40.8) &
                (stops_df['stop_lon'] >= -74.0) & (stops_df['stop_lon'] <= -73.95)
            ].copy()
            
            # Use first 50 stops for simplicity
            important_stops = manhattan_stops.head(50)
            
            # Create route colors
            route_colors = {
                "M1": "#FF6B6B", "M2": "#4ECDC4", "M3": "#45B7D1", "M4": "#96CEB4",
                "M5": "#FFEAA7", "M7": "#DDA0DD", "M10": "#98D8C8", "M11": "#F39C12",
                "M14A": "#E74C3C", "M14D": "#9B59B6", "M15": "#1ABC9C", "M15-SBS": "#2ECC71"
            }
            
            # Create stops and map to street grid
            for _, stop in important_stops.iterrows():
                stop_id = str(stop['stop_id'])
                stop_lat = float(stop['stop_lat'])
                stop_lon = float(stop['stop_lon'])
                
                # Convert lat/lon to simple grid coordinates
                avenue, street = self._latlon_to_grid(stop_lat, stop_lon)
                
                # Assign routes
                available_routes = list(route_colors.keys())
                assigned_routes = random.sample(available_routes, min(2, len(available_routes)))
                
                self.stops[stop_id] = BusStop(
                    stop_id=stop_id,
                    stop_name=stop['stop_name'],
                    lat=stop_lat,
                    lon=stop_lon,
                    avenue=avenue,
                    street=street,
                    routes_served=assigned_routes
                )
            
            # Create simple routes
            all_stop_ids = list(self.stops.keys())
            
            for route_id, color in route_colors.items():
                if len(all_stop_ids) >= 3:
                    # Create simple routes (3-5 stops)
                    num_stops = random.randint(3, 5)
                    route_stops = random.sample(all_stop_ids, num_stops)
                    
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
    
    def _latlon_to_grid(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert lat/lon to simple grid coordinates"""
        # Manhattan bounds
        min_lat, max_lat = 40.7, 40.8
        min_lon, max_lon = -74.0, -73.95
        
        # Convert to grid (1-12 avenues, 1-200 streets)
        avenue = max(1, min(12, int((lon - min_lon) / (max_lon - min_lon) * 12) + 1))
        street = max(1, min(200, int((lat - min_lat) / (max_lat - min_lat) * 200) + 1))
        
        return avenue, street
    
    def _grid_to_latlon(self, avenue: int, street: int) -> Tuple[float, float]:
        """Convert grid coordinates back to lat/lon"""
        min_lat, max_lat = 40.7, 40.8
        min_lon, max_lon = -74.0, -73.95
        
        lat = min_lat + (street - 1) / 200 * (max_lat - min_lat)
        lon = min_lon + (avenue - 1) / 12 * (max_lon - min_lon)
        
        return lat, lon
    
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
        """Initialize buses on street grid"""
        bus_id = 0
        for route_id, route_info in self.routes.items():
            if len(route_info['stops']) >= 2:
                num_buses = random.randint(2, 4)
                for i in range(num_buses):
                    start_stop = self.stops[route_info['stops'][0]]
                    
                    bus = Bus(
                        id=bus_id,
                        route_id=route_id,
                        route_name=route_info['name'],
                        avenue=start_stop.avenue,
                        street=start_stop.street,
                        color=route_info['color']
                    )
                    
                    # Set target to next stop
                    if len(route_info['stops']) > 1:
                        next_stop = self.stops[route_info['stops'][1]]
                        bus.target_avenue = next_stop.avenue
                        bus.target_street = next_stop.street
                    
                    self.buses[bus_id] = bus
                    bus_id += 1
        
        print(f"✅ Initialized {len(self.buses)} buses on street grid")
    
    def step(self):
        """Step the simulation with street-only movement"""
        self.simulation_time += 1
        
        # Generate passengers
        for stop in self.stops.values():
            if random.random() < self.passenger_generation_rate:
                stop.queue_length = min(stop.queue_length + random.randint(1, 2), self.max_passengers_at_stop)
        
        # Move buses on street grid
        for bus in self.buses.values():
            self._move_bus_on_streets(bus)
    
    def _move_bus_on_streets(self, bus: Bus):
        """Move bus only on streets (avenues and streets)"""
        # Simple movement: move one step towards target
        if bus.avenue != bus.target_avenue:
            # Move along avenue
            if bus.avenue < bus.target_avenue:
                bus.avenue += 1
                bus.direction = "east"
            else:
                bus.avenue -= 1
                bus.direction = "west"
        elif bus.street != bus.target_street:
            # Move along street
            if bus.street < bus.target_street:
                bus.street += 1
                bus.direction = "north"
            else:
                bus.street -= 1
                bus.direction = "south"
        else:
            # Reached target, find next stop
            self._find_next_stop(bus)
    
    def _find_next_stop(self, bus: Bus):
        """Find next stop for bus"""
        route = self.routes[bus.route_id]
        current_stop_idx = None
        
        # Find current stop index
        for i, stop_id in enumerate(route['stops']):
            stop = self.stops[stop_id]
            if stop.avenue == bus.avenue and stop.street == bus.street:
                current_stop_idx = i
                break
        
        if current_stop_idx is not None:
            # Move to next stop
            next_stop_idx = (current_stop_idx + 1) % len(route['stops'])
            next_stop = self.stops[route['stops'][next_stop_idx]]
            bus.target_avenue = next_stop.avenue
            bus.target_street = next_stop.street
            
            # Pick up passengers
            self._pickup_passengers(bus)
        else:
            # Random movement if not at a stop
            bus.target_avenue = random.randint(1, 12)
            bus.target_street = random.randint(1, 200)
    
    def _pickup_passengers(self, bus: Bus):
        """Pick up passengers at current location"""
        for stop in self.stops.values():
            if stop.avenue == bus.avenue and stop.street == bus.street:
                if stop.queue_length > 0:
                    pickup = min(random.randint(1, 3), stop.queue_length, bus.capacity - bus.load)
                    bus.load += pickup
                    stop.queue_length -= pickup
                break
    
    def get_system_state(self):
        """Get current system state"""
        total_passengers_waiting = sum(stop.queue_length for stop in self.stops.values())
        total_passengers_on_buses = sum(bus.load for bus in self.buses.values())
        
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
                "street": bus.street
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
    print("🗽 Starting Simple Manhattan Street System...")
    manhattan_system = SimpleManhattanSystem()
    print("✅ Simple Manhattan street system initialized!")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch - Simple Streets</title>
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
      <div class="muted">Simple Street Grid System</div>
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
      console.log('Connected to simple street system');
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
            ['>', ['get', 'queue_length'], 10], '#ef4444',
            ['>', ['get', 'queue_length'], 5], '#f59e0b',
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
          direction: bus.direction,
          avenue: bus.avenue,
          street: bus.street
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
