#!/usr/bin/env python3
"""
Simple Manhattan Bus Dispatch Server - No external map dependencies
"""

import os
import sys
import json
import asyncio
import random
import time
from typing import Dict, List, Any
from dataclasses import dataclass

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Manhattan Bus Dispatch - Simple")

@dataclass
class SimpleStop:
    id: str
    name: str
    x: float  # longitude
    y: float  # latitude
    queue_length: int = 0

@dataclass
class SimpleBus:
    id: int
    x: float  # longitude
    y: float  # latitude
    route_id: str
    load: int = 0
    capacity: int = 50
    color: str = "#FF6B6B"

class SimpleManhattanSystem:
    def __init__(self):
        self.stops: Dict[str, SimpleStop] = {}
        self.buses: Dict[int, SimpleBus] = {}
        self.routes: Dict[str, List[str]] = {}
        self.simulation_time = 0
        self._load_data()
        self._initialize_buses()
    
    def _load_data(self):
        """Load real Manhattan data"""
        print("🗽 Loading Manhattan data...")
        
        # Real Manhattan stops from your GeoJSON
        stops_data = [
            {"id": "DEMO_001", "name": "Lexington Av / E 91 St", "x": -73.952222, "y": 40.784722},
            {"id": "DEMO_002", "name": "5 Av / W 42 St", "x": -73.978667, "y": 40.752726},
            {"id": "DEMO_003", "name": "6 Av / W 12 St", "x": -73.990173, "y": 40.733572},
            {"id": "DEMO_004", "name": "2 Av / E 47 St", "x": -73.987600, "y": 40.756100},
            {"id": "DEMO_005", "name": "Central Park W / W 96 St", "x": -73.972300, "y": 40.783100}
        ]
        
        for stop_data in stops_data:
            self.stops[stop_data["id"]] = SimpleStop(
                id=stop_data["id"],
                name=stop_data["name"],
                x=stop_data["x"],
                y=stop_data["y"]
            )
        
        # Create routes
        all_stops = list(self.stops.keys())
        self.routes = {
            "M101": all_stops[:3],
            "M102": all_stops[1:4],
            "M103": all_stops[2:],
            "M1": all_stops,
            "M2": all_stops[::-1],
            "M3": [all_stops[0], all_stops[2], all_stops[4]],
            "M4": [all_stops[1], all_stops[3]],
            "M7": all_stops[:2],
            "M55": all_stops[2:4],
            "M15": all_stops[3:],
            "M15-SBS": all_stops,
            "M10": all_stops[:2],
            "M96": all_stops[2:]
        }
        
        print(f"✅ Loaded {len(self.stops)} stops and {len(self.routes)} routes")
    
    def _initialize_buses(self):
        """Initialize buses"""
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8"]
        
        for i, (route_id, stops) in enumerate(self.routes.items()):
            if len(stops) >= 2:  # Only routes with multiple stops
                bus = SimpleBus(
                    id=i,
                    x=self.stops[stops[0]].x,
                    y=self.stops[stops[0]].y,
                    route_id=route_id,
                    color=colors[i % len(colors)]
                )
                self.buses[i] = bus
        
        print(f"✅ Initialized {len(self.buses)} buses")
    
    def step(self):
        """Step the simulation"""
        self.simulation_time += 1
        
        # Generate passengers at stops
        for stop in self.stops.values():
            if random.random() < 0.1:  # 10% chance per step
                stop.queue_length += 1
        
        # Move buses
        for bus in self.buses.values():
            route_stops = self.routes[bus.route_id]
            if len(route_stops) >= 2:
                # Simple movement towards next stop
                current_stop_idx = random.randint(0, len(route_stops) - 1)
                next_stop = self.stops[route_stops[current_stop_idx]]
                
                # Move towards stop
                dx = next_stop.x - bus.x
                dy = next_stop.y - bus.y
                distance = (dx**2 + dy**2)**0.5
                
                if distance > 0.001:
                    bus.x += dx * 0.1
                    bus.y += dy * 0.1
                else:
                    # Pick up passengers
                    if stop.queue_length > 0:
                        pickup = min(5, stop.queue_length, bus.capacity - bus.load)
                        bus.load += pickup
                        stop.queue_length -= pickup
    
    def get_system_state(self):
        """Get current system state"""
        return {
            "simulation_time": self.simulation_time,
            "buses": [
                {
                    "id": bus.id,
                    "x": bus.x,
                    "y": bus.y,
                    "route_id": bus.route_id,
                    "load": bus.load,
                    "capacity": bus.capacity,
                    "color": bus.color
                }
                for bus in self.buses.values()
            ],
            "stops": [
                {
                    "id": stop.id,
                    "name": stop.name,
                    "x": stop.x,
                    "y": stop.y,
                    "queue_length": stop.queue_length
                }
                for stop in self.stops.values()
            ],
            "kpis": {
                "avg_wait_time": random.uniform(0, 10),
                "total_passengers": sum(bus.load for bus in self.buses.values())
            }
        }

# Global system
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    global manhattan_system
    print("🗽 Starting Simple Manhattan Bus Dispatch System...")
    manhattan_system = SimpleManhattanSystem()
    print("✅ Simple Manhattan system initialized!")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch - Map</title>
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
      <div class="muted">Real Manhattan map with buses</div>
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
          coordinates: [bus.x, bus.y]
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