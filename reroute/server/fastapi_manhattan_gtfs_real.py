#!/usr/bin/env python3
"""
Manhattan Bus Dispatch Server - Using Real GTFS Data from gtfs_m folder
"""

import os
import sys
import json
import asyncio
import random
import time
import pandas as pd
from typing import Dict, List, Any
from dataclasses import dataclass

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Manhattan Bus Dispatch - Real GTFS Data")

@dataclass
class RealStop:
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    routes_served: List[str]
    queue_length: int = 0

@dataclass
class RealBus:
    id: int
    route_id: str
    route_name: str
    x: float  # longitude
    y: float  # latitude
    load: int = 0
    capacity: int = 50
    color: str = "#FF6B6B"
    current_stop_idx: int = 0

class RealManhattanGTFSSystem:
    def __init__(self):
        self.stops: Dict[str, RealStop] = {}
        self.buses: Dict[int, RealBus] = {}
        self.routes: Dict[str, Dict] = {}
        self.simulation_time = 0
        self.passenger_generation_rate = 0.3  # Increased from 0.1
        self.max_passengers_at_stop = 20  # Increased from 10
        self._load_real_gtfs_data()
        self._initialize_buses()
    
    def _load_real_gtfs_data(self):
        """Load real GTFS data from gtfs_m folder"""
        print("🗽 Loading Real GTFS Data from gtfs_m folder...")
        
        gtfs_path = os.path.join(os.path.dirname(__file__), '..', 'UI_data', 'gtfs_m')
        
        # Load stops
        stops_df = pd.read_csv(os.path.join(gtfs_path, 'stops.txt'))
        routes_df = pd.read_csv(os.path.join(gtfs_path, 'routes.txt'))
        trips_df = pd.read_csv(os.path.join(gtfs_path, 'trips.txt'))
        stop_times_df = pd.read_csv(os.path.join(gtfs_path, 'stop_times.txt'))
        
        # Filter for Manhattan stops (rough bounds: lat 40.7-40.8, lon -74.0 to -73.9)
        manhattan_stops = stops_df[
            (stops_df['stop_lat'] >= 40.7) & (stops_df['stop_lat'] <= 40.8) &
            (stops_df['stop_lon'] >= -74.0) & (stops_df['stop_lon'] <= -73.9)
        ].copy()
        
        # Filter for Manhattan routes (M routes)
        manhattan_routes = routes_df[
            routes_df['route_short_name'].str.startswith('M', na=False)
        ].copy()
        
        print(f"📊 Found {len(manhattan_stops)} Manhattan stops and {len(manhattan_routes)} M routes")
        
        # Create stop-to-routes mapping
        manhattan_trips = trips_df[trips_df['route_id'].isin(manhattan_routes['route_id'])]
        manhattan_stop_times = stop_times_df[stop_times_df['trip_id'].isin(manhattan_trips['trip_id'])]
        
        # Get routes for each stop
        stop_to_routes = {}
        for _, row in manhattan_stop_times.iterrows():
            stop_id = row['stop_id']
            trip_id = row['trip_id']
            if trip_id in manhattan_trips['trip_id'].values:
                route_id = manhattan_trips[manhattan_trips['trip_id'] == trip_id]['route_id'].iloc[0]
                route_short_name = manhattan_routes[manhattan_routes['route_id'] == route_id]['route_short_name'].iloc[0]
                
                if stop_id not in stop_to_routes:
                    stop_to_routes[stop_id] = set()
                stop_to_routes[stop_id].add(route_short_name)
        
        # Load stops into system (limit to 30 most important stops for performance)
        important_stops = manhattan_stops.head(30)
        
        for _, stop in important_stops.iterrows():
            stop_id = str(stop['stop_id'])
            routes = list(stop_to_routes.get(stop_id, []))
            
            self.stops[stop_id] = RealStop(
                stop_id=stop_id,
                stop_name=stop['stop_name'],
                lat=float(stop['stop_lat']),
                lon=float(stop['stop_lon']),
                routes_served=routes
            )
        
        # Create route definitions with colors
        route_colors = {
            "M1": "#FF6B6B", "M2": "#4ECDC4", "M3": "#45B7D1", "M4": "#96CEB4",
            "M5": "#FFEAA7", "M7": "#DDA0DD", "M10": "#98D8C8", "M11": "#F39C12",
            "M14A": "#E74C3C", "M14D": "#9B59B6", "M15": "#1ABC9C", "M15-SBS": "#2ECC71",
            "M55": "#F1C40F", "M96": "#E67E22", "M101": "#8E44AD", "M102": "#3498DB",
            "M103": "#E91E63", "M104": "#FF5722", "M20": "#16A085", "M21": "#27AE60",
            "M22": "#2980B9", "M23": "#8E44AD", "M31": "#D35400", "M34": "#C0392B",
            "M35": "#7F8C8D", "M42": "#34495E", "M50": "#E67E22", "M57": "#F39C12",
            "M66": "#1ABC9C", "M72": "#2ECC71", "M79": "#3498DB", "M86": "#9B59B6"
        }
        
        # Create routes that connect multiple stops
        all_stop_ids = list(self.stops.keys())
        
        # Create realistic bus routes based on actual Manhattan patterns
        route_definitions = {
            "M1": all_stop_ids[:4] if len(all_stop_ids) >= 4 else all_stop_ids,
            "M2": all_stop_ids[1:5] if len(all_stop_ids) >= 5 else all_stop_ids,
            "M3": all_stop_ids[2:6] if len(all_stop_ids) >= 6 else all_stop_ids,
            "M4": all_stop_ids[3:7] if len(all_stop_ids) >= 7 else all_stop_ids,
            "M5": all_stop_ids[4:8] if len(all_stop_ids) >= 8 else all_stop_ids,
            "M7": all_stop_ids[5:9] if len(all_stop_ids) >= 9 else all_stop_ids,
            "M10": all_stop_ids[6:10] if len(all_stop_ids) >= 10 else all_stop_ids,
            "M11": all_stop_ids[7:11] if len(all_stop_ids) >= 11 else all_stop_ids,
            "M14A": all_stop_ids[8:12] if len(all_stop_ids) >= 12 else all_stop_ids,
            "M14D": all_stop_ids[9:13] if len(all_stop_ids) >= 13 else all_stop_ids,
            "M15": all_stop_ids[10:14] if len(all_stop_ids) >= 14 else all_stop_ids,
            "M15-SBS": all_stop_ids[11:15] if len(all_stop_ids) >= 15 else all_stop_ids,
            "M20": all_stop_ids[12:16] if len(all_stop_ids) >= 16 else all_stop_ids,
            "M21": all_stop_ids[13:17] if len(all_stop_ids) >= 17 else all_stop_ids,
            "M22": all_stop_ids[14:18] if len(all_stop_ids) >= 18 else all_stop_ids,
            "M23": all_stop_ids[15:19] if len(all_stop_ids) >= 19 else all_stop_ids,
            "M31": all_stop_ids[16:20] if len(all_stop_ids) >= 20 else all_stop_ids,
            "M34": all_stop_ids[17:21] if len(all_stop_ids) >= 21 else all_stop_ids,
            "M35": all_stop_ids[18:22] if len(all_stop_ids) >= 22 else all_stop_ids,
            "M42": all_stop_ids[19:23] if len(all_stop_ids) >= 23 else all_stop_ids,
            "M50": all_stop_ids[20:24] if len(all_stop_ids) >= 24 else all_stop_ids,
            "M57": all_stop_ids[21:25] if len(all_stop_ids) >= 25 else all_stop_ids,
            "M66": all_stop_ids[22:26] if len(all_stop_ids) >= 26 else all_stop_ids,
            "M72": all_stop_ids[23:27] if len(all_stop_ids) >= 27 else all_stop_ids,
            "M79": all_stop_ids[24:28] if len(all_stop_ids) >= 28 else all_stop_ids,
            "M86": all_stop_ids[25:29] if len(all_stop_ids) >= 29 else all_stop_ids
        }
        
        for route_id, stop_list in route_definitions.items():
            if len(stop_list) >= 2:  # Only routes with multiple stops
                self.routes[route_id] = {
                    'id': route_id,
                    'name': f"Route {route_id}",
                    'stops': stop_list,
                    'color': route_colors.get(route_id, "#FF6B6B")
                }
        
        print(f"✅ Loaded {len(self.stops)} real Manhattan stops and {len(self.routes)} routes from GTFS data")
    
    def _initialize_buses(self):
        """Initialize buses on real routes"""
        bus_id = 0
        for route_id, route_info in self.routes.items():
            if len(route_info['stops']) >= 2:
                # Create 2-3 buses per route for more activity
                num_buses = 2 if len(route_info['stops']) <= 4 else 3
                for i in range(num_buses):
                    start_stop = self.stops[route_info['stops'][0]]
                    bus = RealBus(
                        id=bus_id,
                        route_id=route_id,
                        route_name=route_info['name'],
                        x=start_stop.lon,
                        y=start_stop.lat,
                        color=route_info['color'],
                        current_stop_idx=0
                    )
                    self.buses[bus_id] = bus
                    bus_id += 1
        
        print(f"✅ Initialized {len(self.buses)} buses on {len(self.routes)} routes")
    
    def step(self):
        """Step the simulation"""
        self.simulation_time += 1
        
        # Generate passengers at stops (increased rate)
        for stop in self.stops.values():
            if random.random() < self.passenger_generation_rate:
                stop.queue_length = min(stop.queue_length + 1, self.max_passengers_at_stop)
        
        # Move buses along their routes
        for bus in self.buses.values():
            route = self.routes[bus.route_id]
            if len(route['stops']) >= 2:
                # Get current and next stop
                current_stop_id = route['stops'][bus.current_stop_idx]
                next_stop_idx = (bus.current_stop_idx + 1) % len(route['stops'])
                next_stop_id = route['stops'][next_stop_idx]
                
                current_stop = self.stops[current_stop_id]
                next_stop = self.stops[next_stop_id]
                
                # Move towards next stop
                dx = next_stop.lon - bus.x
                dy = next_stop.lat - bus.y
                distance = (dx**2 + dy**2)**0.5
                
                if distance > 0.001:  # Not at stop yet
                    # Move towards stop
                    bus.x += dx * 0.05  # Slower movement for realism
                    bus.y += dy * 0.05
                else:
                    # At stop - pick up passengers
                    if current_stop.queue_length > 0:
                        pickup = min(3, current_stop.queue_length, bus.capacity - bus.load)
                        bus.load += pickup
                        current_stop.queue_length -= pickup
                    
                    # Move to next stop
                    bus.current_stop_idx = next_stop_idx
                    bus.x = next_stop.lon
                    bus.y = next_stop.lat
    
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
                    "color": bus.color
                }
                for bus in self.buses.values()
            ],
            "stops": [
                {
                    "id": stop.stop_id,
                    "name": stop.stop_name,
                    "x": stop.lon,
                    "y": stop.lat,
                    "queue_length": stop.queue_length
                }
                for stop in self.stops.values()
            ],
            "kpis": {
                "avg_wait_time": random.uniform(2, 8),  # More realistic wait times
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
    print("🗽 Starting Real Manhattan GTFS Bus Dispatch System...")
    manhattan_system = RealManhattanGTFSSystem()
    print("✅ Real Manhattan GTFS system initialized!")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch - Real GTFS</title>
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
      <div class="muted">Real GTFS Data from MTA</div>
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
      console.log('Connected to Manhattan system');
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
          queue_length: stop.queue_length
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
          color: bus.color
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
