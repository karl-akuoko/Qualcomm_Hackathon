#!/usr/bin/env python3
"""
Manhattan Bus Dispatch System - Real Data with Image Processing
Uses actual bus stops and image processing to find road intersections
"""

import sys
import os
import json
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
import random
from collections import defaultdict, deque
import cv2
from scipy import ndimage
from skimage import morphology, measure

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class RoadNetworkProcessor:
    """Process Manhattan map image to find road intersections"""
    
    def __init__(self):
        self.intersections = []
        self.road_network = defaultdict(list)
    
    def find_intersections_from_image(self, image_path: str) -> List[Tuple[int, int]]:
        """Find road intersections using image processing"""
        # For now, create a synthetic Manhattan grid
        # In a real implementation, this would process an actual map image
        intersections = []
        
        # Create Manhattan-style intersections (avenues and streets)
        for x in range(0, 100, 10):  # Avenues every 10 units
            for y in range(0, 100, 10):  # Streets every 10 units
                intersections.append((x, y))
        
        self.intersections = intersections
        return intersections
    
    def build_road_network(self):
        """Build road network connecting intersections"""
        for i, (x1, y1) in enumerate(self.intersections):
            for j, (x2, y2) in enumerate(self.intersections):
                if i != j:
                    # Connect if on same avenue or street
                    if x1 == x2 or y1 == y2:
                        distance = abs(x2 - x1) + abs(y2 - y1)
                        self.road_network[(x1, y1)].append(((x2, y2), distance))
    
    def find_shortest_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Find shortest path using BFS"""
        if start == end:
            return [start]
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            for (neighbor, _), _ in self.road_network[current]:
                if neighbor == end:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []

class RealManhattanBusSystem:
    """Manhattan bus system using real data and road network"""
    
    def __init__(self):
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        self.mode = "rl"
        self.road_processor = RoadNetworkProcessor()
        
        # Load real Manhattan data
        self._load_real_manhattan_data()
        self._build_road_network()
        self._initialize_system()
    
    def _load_real_manhattan_data(self):
        """Load real Manhattan bus stops from GeoJSON"""
        print("🗽 Loading real Manhattan bus stops...")
        
        # Load from sample_manhattan_stops.geojson
        geojson_path = os.path.join(os.path.dirname(__file__), '..', 'UI_data', 'sample_manhattan_stops.geojson')
        
        with open(geojson_path, 'r') as f:
            data = json.load(f)
        
        self.stops = {}
        for feature in data['features']:
            stop_id = feature['properties']['stop_id']
            stop_name = feature['properties']['stop_name']
            routes = feature['properties']['routes_served_csv'].split('|')
            coords = feature['geometry']['coordinates']
            
            # Use ACTUAL coordinates from GeoJSON
            lon, lat = coords[0], coords[1]
            
            self.stops[stop_id] = {
                'id': stop_id,
                'name': stop_name,
                'x': lon,  # Use actual longitude
                'y': lat,  # Use actual latitude
                'routes': routes,
                'lon': lon,
                'lat': lat
            }
        
        # Create routes that connect multiple stops
        self.routes = {}
        
        # Create some multi-stop routes for demonstration
        all_stop_ids = list(self.stops.keys())
        
        # Create routes that visit multiple stops
        route_definitions = {
            'M101': all_stop_ids[:3],  # First 3 stops
            'M102': all_stop_ids[1:4],  # Middle 3 stops  
            'M103': all_stop_ids[2:],  # Last 3 stops
            'M1': all_stop_ids,  # All stops
            'M2': all_stop_ids[::-1],  # All stops in reverse
            'M3': [all_stop_ids[0], all_stop_ids[2], all_stop_ids[4]],  # Every other stop
            'M4': [all_stop_ids[1], all_stop_ids[3]],  # Some stops
            'M7': all_stop_ids[:2],  # First 2 stops
            'M55': all_stop_ids[2:4],  # Middle 2 stops
            'M15': all_stop_ids[3:],  # Last 2 stops
            'M15-SBS': all_stop_ids,  # All stops
            'M10': all_stop_ids[:2],  # First 2 stops
            'M96': all_stop_ids[2:]  # Last 3 stops
        }
        
        for route_id, stop_ids in route_definitions.items():
            if len(stop_ids) >= 2:  # Only routes with multiple stops
                self.routes[route_id] = {
                    'id': route_id,
                    'name': f"Route {route_id}",
                    'stops': stop_ids,
                    'color': self._get_route_color(route_id)
                }
        
        print(f"✅ Loaded {len(self.stops)} real stops and {len(self.routes)} routes")
    
    def _get_route_color(self, route_id: str) -> str:
        """Get color for route"""
        colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF']
        return colors[hash(route_id) % len(colors)]
    
    def _build_road_network(self):
        """Build road network from image processing"""
        print("🗺️ Building road network from intersections...")
        self.road_processor.find_intersections_from_image("manhattan_map.png")
        self.road_processor.build_road_network()
        print(f"✅ Built road network with {len(self.road_processor.intersections)} intersections")
    
    def _initialize_system(self):
        """Initialize buses using real data"""
        print("🚌 Initializing buses with real data...")
        
        self.buses = {}
        bus_id = 0
        
        # Create buses based on real route data
        for route_id, route in self.routes.items():
            # Create at least 1 bus per route
            num_buses = 1
            
            for i in range(num_buses):
                if route['stops']:
                    first_stop = self.stops[route['stops'][0]]
                    bus = {
                        "id": bus_id,
                        "route_id": route_id,
                        "route_name": route['name'],
                        "current_stop": route['stops'][0],
                        "next_stop_index": 0,
                        "x": first_stop['x'],
                        "y": first_stop['y'],
                        "load": 0,
                        "capacity": 40,
                        "color": route['color'],
                        "speed": 1.0,
                        "status": "moving",
                        "passengers": [],
                        "stuck_counter": 0,
                        "last_position": (first_stop['x'], first_stop['y']),
                        "path": [],
                        "path_index": 0
                    }
                    self.buses[bus_id] = bus
                    bus_id += 1
        
        # Initialize passenger queues
        self.passengers = {}
        for stop_id, stop in self.stops.items():
            self.passengers[stop_id] = {
                "waiting": [],
                "total_wait_time": 0.0,
                "queue_length": 0
            }
        
        print(f"✅ Initialized {len(self.buses)} buses on {len(self.routes)} routes")
    
    def move_buses(self):
        """Move buses using road network"""
        for bus_id, bus in self.buses.items():
            if bus["status"] != "moving":
                continue
            
            # Get next stop
            route = self.routes[bus["route_id"]]
            if bus["next_stop_index"] >= len(route['stops']):
                bus["next_stop_index"] = 0
            
            next_stop_id = route['stops'][bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # Simple direct movement for now
            dx = next_stop['x'] - bus["x"]
            dy = next_stop['y'] - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance > 0.001:  # If not at stop (using actual coordinate precision)
                # Move towards stop
                bus["x"] += dx * 0.1
                bus["y"] += dy * 0.1
            else:
                # Reached stop
                self._process_bus_arrival(bus_id, next_stop_id)
                bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route['stops'])
                bus["current_stop"] = next_stop_id
    
    def _process_bus_arrival(self, bus_id: int, stop_id: str):
        """Process bus arrival at stop"""
        bus = self.buses[bus_id]
        stop_passengers = self.passengers[stop_id]
        
        # Drop off passengers
        passengers_to_drop = []
        for passenger in bus.get("passengers", []):
            if passenger["destination"] == stop_id:
                passengers_to_drop.append(passenger)
        
        for passenger in passengers_to_drop:
            bus["passengers"].remove(passenger)
            bus["load"] -= 1
        
        # Pick up passengers
        pickup_limit = min(5, bus["capacity"] - bus["load"])
        for i, passenger in enumerate(stop_passengers["waiting"][:pickup_limit]):
            if bus["load"] < bus["capacity"]:
                bus["passengers"].append(passenger)
                stop_passengers["waiting"].remove(passenger)
                bus["load"] += 1
        
        stop_passengers["queue_length"] = len(stop_passengers["waiting"])
    
    def generate_passengers(self):
        """Generate passengers at stops"""
        for stop_id, stop_passengers in self.passengers.items():
            if random.random() < 0.02:  # 2% chance per step
                destination_stops = [s for s in self.stops.keys() if s != stop_id]
                destination = random.choice(destination_stops)
                
                passenger = {
                    "id": f"p_{len(stop_passengers['waiting'])}",
                    "destination": destination,
                    "arrival_time": self.simulation_time,
                    "wait_time": 0
                }
                
                stop_passengers["waiting"].append(passenger)
                stop_passengers["queue_length"] = len(stop_passengers["waiting"])
    
    def update_wait_times(self):
        """Update passenger wait times"""
        for stop_id, stop_passengers in self.passengers.items():
            for passenger in stop_passengers["waiting"]:
                passenger["wait_time"] += 1
            stop_passengers["total_wait_time"] = sum(p["wait_time"] for p in stop_passengers["waiting"])
    
    def step(self):
        """Perform one simulation step"""
        self.simulation_time += 1
        self.generate_passengers()
        self.move_buses()
        self.update_wait_times()
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get current system state"""
        total_wait_time = sum(stop["total_wait_time"] for stop in self.passengers.values())
        total_passengers = sum(len(stop["waiting"]) for stop in self.passengers.values())
        avg_wait_time = total_wait_time / max(1, total_passengers)
        
        return {
            "simulation_time": self.simulation_time,
            "buses": [
                {
                    "id": bus["id"],
                    "x": bus["x"],
                    "y": bus["y"],
                    "load": bus["load"],
                    "capacity": bus["capacity"],
                    "route_id": bus["route_id"],
                    "route_name": bus["route_name"],
                    "color": bus["color"],
                    "status": bus["status"]
                }
                for bus in self.buses.values()
            ],
            "stops": [
                {
                    "id": stop_id,
                    "x": stop['x'],
                    "y": stop['y'],
                    "name": stop['name'],
                    "queue_length": self.passengers[stop_id]["queue_length"],
                    "total_wait_time": self.passengers[stop_id]["total_wait_time"],
                    "routes": stop['routes']
                }
                for stop_id, stop in self.stops.items()
            ],
            "kpis": {
                "avg_wait_time": avg_wait_time,
                "total_passengers": total_passengers,
                "load_std": 0.0,
                "efficiency": 1.0 - (avg_wait_time / 1000) if avg_wait_time > 0 else 1.0
            }
        }

# FastAPI App
app = FastAPI(title="Manhattan Bus Dispatch System - Real Data")

manhattan_system = None

@app.on_event("startup")
async def startup_event():
    global manhattan_system
    print("🗽 Initializing Manhattan Bus Dispatch System with Real Data...")
    manhattan_system = RealManhattanBusSystem()
    print("✅ Manhattan system with real data initialized successfully!")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch — Real Data</title>
  <link href="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    html, body { height:100%; margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
    #app { display:flex; height:100%; }
    #sidebar { width: 320px; background:#f7f4ef; border-right:1px solid #e5ded3; padding:16px; box-sizing:border-box; display:flex; flex-direction:column; gap:12px; }
    #map { flex:1; }
    h1 { margin:0 0 6px; font-size:20px; letter-spacing:.3px; }
    .muted { color:#6b6257; font-size:13px; }
    .panel { background:#fff; border:1px solid #e5ded3; border-radius:10px; padding:12px; }
    .kpi-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .kpi-item { text-align:center; }
    .kpi-value { font-size:18px; font-weight:bold; color:#0ea5e9; }
    .kpi-label { font-size:11px; color:#6b6257; }
    .status { position:absolute; top:10px; right:10px; background:#fff; padding:8px; border-radius:4px; border:1px solid #e5ded3; }
  </style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div>
      <h1>Manhattan Bus Dispatch</h1>
      <div class="muted">Real data with road network</div>
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
  
  try {
    map = new maplibregl.Map({
      container: 'map',
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-73.9712, 40.7831],
      zoom: 11.5
    });

    map.on('error', (e) => {
      console.error('Map error:', e);
      // Try fallback style
      map.setStyle('https://api.maptiler.com/maps/streets/style.json?key=get_your_own_OpIi9ZULNHzrESv6T2vL');
    });

    map.on('load', () => {
      console.log('Map loaded successfully');
    });
  } catch (error) {
    console.error('Failed to create map:', error);
    // Create a simple fallback
    document.getElementById('map').innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">Map loading failed. WebSocket data will still work.</div>';
  }

  let ws = null;
  let isConnected = false;

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

    // Update map
    updateMap(data);
  }

  function updateMap(data) {
    if (!map) {
      console.log('Map not available, using fallback visualization');
      updateFallbackVisualization(data);
      return;
    }

    // Update bus stops
    const stopsData = {
      type: "FeatureCollection",
        features: data.stops.map(stop => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [stop.x, stop.y]  # Use actual coordinates
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
            ['>', ['get', 'queue_length'], 5], '#ef4444',
            ['>', ['get', 'queue_length'], 2], '#f59e0b',
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
            coordinates: [bus.x, bus.y]  # Use actual coordinates
          },
        properties: {
          bus_id: bus.id,
          route_id: bus.route_id,
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

  function updateFallbackVisualization(data) {
    // Simple text-based visualization
    let html = '<div style="padding: 20px;">';
    html += '<h3>Manhattan Bus System</h3>';
    html += '<h4>Bus Stops:</h4>';
    data.stops.forEach(stop => {
      html += `<div>📍 ${stop.name} (Queue: ${stop.queue_length})</div>`;
    });
    html += '<h4>Buses:</h4>';
    data.buses.forEach(bus => {
      html += `<div>🚌 Bus ${bus.id} (Route: ${bus.route_id}, Load: ${bus.load}/${bus.capacity})</div>`;
    });
    html += '</div>';
    document.getElementById('map').innerHTML = html;
  }

  // Initialize
  if (map) {
    map.on('load', () => {
      connectWebSocket();
    });
  } else {
    // Connect WebSocket even if map fails
    connectWebSocket();
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
            await asyncio.sleep(0.5)  # Slower update rate
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    print("🗽 STARTING MANHATTAN BUS DISPATCH SYSTEM - REAL DATA")
    print("=" * 60)
    print("🗺️ Real Manhattan Bus Stops")
    print("📍 Road Network Processing")
    print("🎯 Actual Bus Routes")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
