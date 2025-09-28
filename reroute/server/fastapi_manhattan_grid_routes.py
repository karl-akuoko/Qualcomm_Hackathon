#!/usr/bin/env python3
"""
Manhattan Bus Dispatch System - Grid Route Following
Buses follow actual NYC street gridlines for realistic movement
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

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rl'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from manhattan_data_parser import ManhattanDataParser, ManhattanStop, ManhattanRoute

class ManhattanGridRouter:
    """Router that follows Manhattan street gridlines"""
    
    def __init__(self, grid_size: int = 100):
        self.grid_size = grid_size
        self.streets = self._create_street_grid()
    
    def _create_street_grid(self):
        """Create Manhattan street grid with avenues and streets"""
        streets = {}
        
        # Create avenues (north-south)
        for x in range(0, self.grid_size, 5):  # Every 5 units
            streets[f"avenue_{x}"] = {
                "type": "avenue",
                "x": x,
                "direction": "north_south",
                "name": f"Avenue {x//5 + 1}"
            }
        
        # Create streets (east-west)
        for y in range(0, self.grid_size, 5):  # Every 5 units
            streets[f"street_{y}"] = {
                "type": "street", 
                "y": y,
                "direction": "east_west",
                "name": f"Street {y//5 + 1}"
            }
        
        return streets
    
    def find_grid_route(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Find route following Manhattan grid"""
        start_x, start_y = start
        end_x, end_y = end
        
        route = [start]
        current_x, current_y = start_x, start_y
        
        # Manhattan routing: go to nearest avenue, then to destination avenue, then to destination
        # Step 1: Move to nearest avenue (snap to grid)
        nearest_avenue_x = round(current_x / 5) * 5
        if current_x != nearest_avenue_x:
            # Move horizontally to avenue
            while current_x != nearest_avenue_x:
                if current_x < nearest_avenue_x:
                    current_x += 1
                else:
                    current_x -= 1
                route.append((current_x, current_y))
        
        # Step 2: Move to destination avenue
        dest_avenue_x = round(end_x / 5) * 5
        if current_x != dest_avenue_x:
            # Move horizontally to destination avenue
            while current_x != dest_avenue_x:
                if current_x < dest_avenue_x:
                    current_x += 1
                else:
                    current_x -= 1
                route.append((current_x, current_y))
        
        # Step 3: Move to destination street
        nearest_street_y = round(current_y / 5) * 5
        if current_y != nearest_street_y:
            # Move vertically to street
            while current_y != nearest_street_y:
                if current_y < nearest_street_y:
                    current_y += 1
                else:
                    current_y -= 1
                route.append((current_x, current_y))
        
        # Step 4: Move to destination
        while current_y != end_y:
            if current_y < end_y:
                current_y += 1
            else:
                current_y -= 1
            route.append((current_x, current_y))
        
        while current_x != end_x:
            if current_x < end_x:
                current_x += 1
            else:
                current_x -= 1
            route.append((current_x, current_y))
        
        return route

class ManhattanBusDispatchSystem:
    """Manhattan bus dispatch system with grid route following"""
    
    def __init__(self):
        self.parser = ManhattanDataParser()
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        self.mode = "rl"
        self.grid_router = ManhattanGridRouter()
        
        # Load Manhattan data
        self._load_manhattan_data()
        self._initialize_system()
    
    def _load_manhattan_data(self):
        """Load real Manhattan bus data"""
        print("🗽 Loading Manhattan bus data...")
        
        self.stops = self.parser.load_manhattan_stops()
        self.routes = self.parser.create_manhattan_routes()
        
        print(f"✅ Loaded {len(self.stops)} stops and {len(self.routes)} routes")
    
    def _initialize_system(self):
        """Initialize the Manhattan bus system"""
        print("🚌 Initializing Manhattan bus system with grid routes...")
        
        # Create buses for each route
        self.buses = {}
        bus_id = 0
        
        for route_id, route in self.routes.items():
            # Create 2-3 buses per route
            num_buses = 2 if "SBS" in route_id else 3
            
            for i in range(num_buses):
                bus = {
                    "id": bus_id,
                    "route_id": route_id,
                    "route_name": route.route_name,
                    "current_stop": route.stops[0] if route.stops else None,
                    "next_stop_index": 0,
                    "x": self.stops[route.stops[0]].x if route.stops else 0,
                    "y": self.stops[route.stops[0]].y if route.stops else 0,
                    "load": 0,
                    "capacity": 40,
                    "color": route.color,
                    "direction": route.direction,
                    "speed": 1.0,  # Slower for grid movement
                    "status": "moving",
                    "passengers": [],
                    "stuck_counter": 0,
                    "last_position": (self.stops[route.stops[0]].x, self.stops[route.stops[0]].y) if route.stops else (0, 0),
                    "grid_route": [],  # Path following grid
                    "route_index": 0,  # Current position in grid route
                    "target_stop": None  # Next stop to reach
                }
                self.buses[bus_id] = bus
                bus_id += 1
        
        # Initialize passenger queues at stops
        self.passengers = {}
        for stop_id, stop in self.stops.items():
            self.passengers[stop_id] = {
                "waiting": [],
                "total_wait_time": 0.0,
                "queue_length": 0
            }
        
        print(f"✅ Initialized {len(self.buses)} buses on {len(self.routes)} routes with grid routing")
    
    def get_manhattan_demand(self, stop_id: str, hour: int) -> float:
        """Get realistic demand for Manhattan stops"""
        stop = self.stops[stop_id]
        
        # Base demand by location
        base_demand = 1.0
        
        # Major transfer points have higher demand
        if "TRANS" in stop_id:
            base_demand = 2.5
        elif any(route in stop.routes for route in ["M1", "M2", "M3", "M4"]):  # 5th Ave
            base_demand = 1.8
        elif any(route in stop.routes for route in ["M5", "M7", "M104"]):  # Broadway
            base_demand = 1.6
        elif "M14" in stop.routes[0] if stop.routes else False:  # 14th St
            base_demand = 1.4
        
        # Time-based demand patterns
        if 7 <= hour <= 9:  # Morning rush
            time_factor = 1.5
        elif 17 <= hour <= 19:  # Evening rush
            time_factor = 1.3
        elif 10 <= hour <= 16:  # Midday
            time_factor = 0.8
        else:  # Night
            time_factor = 0.3
        
        return base_demand * time_factor
    
    def generate_passengers(self):
        """Generate passengers based on Manhattan demand patterns"""
        current_hour = (self.simulation_time // 3600) % 24
        
        for stop_id, stop in self.stops.items():
            demand = self.get_manhattan_demand(stop_id, current_hour)
            
            # Generate passengers based on demand
            if random.random() < demand * 0.05:  # Reduced rate
                # Create passenger with destination
                destination_stops = [s for s in self.stops.keys() if s != stop_id]
                destination = random.choice(destination_stops)
                
                passenger = {
                    "id": f"p_{len(self.passengers[stop_id]['waiting'])}",
                    "destination": destination,
                    "arrival_time": self.simulation_time,
                    "wait_time": 0
                }
                
                self.passengers[stop_id]["waiting"].append(passenger)
                self.passengers[stop_id]["queue_length"] = len(self.passengers[stop_id]["waiting"])
    
    def move_buses(self):
        """Move buses following Manhattan grid routes"""
        for bus_id, bus in self.buses.items():
            if bus["status"] != "moving":
                continue
            
            # Check if bus is stuck
            current_pos = (bus["x"], bus["y"])
            if current_pos == bus["last_position"]:
                bus["stuck_counter"] += 1
            else:
                bus["stuck_counter"] = 0
                bus["last_position"] = current_pos
            
            # If stuck for too long, force movement
            if bus["stuck_counter"] > 20:  # Longer timeout for grid movement
                self._unstuck_bus(bus_id)
                continue
            
            # Get next stop
            route = self.routes[bus["route_id"]]
            if bus["next_stop_index"] >= len(route.stops):
                bus["next_stop_index"] = 0
            
            next_stop_id = route.stops[bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # If no grid route or reached end of route, calculate new route
            if not bus["grid_route"] or bus["route_index"] >= len(bus["grid_route"]):
                start_pos = (bus["x"], bus["y"])
                end_pos = (next_stop.x, next_stop.y)
                bus["grid_route"] = self.grid_router.find_grid_route(start_pos, end_pos)
                bus["route_index"] = 0
                bus["target_stop"] = next_stop_id
            
            # Move along grid route
            if bus["route_index"] < len(bus["grid_route"]):
                next_pos = bus["grid_route"][bus["route_index"]]
                bus["x"] = next_pos[0]
                bus["y"] = next_pos[1]
                bus["route_index"] += 1
                
                # Check if reached target stop
                if (bus["x"], bus["y"]) == (next_stop.x, next_stop.y):
                    self._process_bus_arrival(bus_id, next_stop_id)
                    bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
                    bus["current_stop"] = next_stop_id
                    bus["grid_route"] = []  # Clear route for next stop
                    bus["route_index"] = 0
    
    def _unstuck_bus(self, bus_id: int):
        """Force unstuck a bus by teleporting to next stop"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        # Move to next stop directly
        next_stop_id = route.stops[bus["next_stop_index"]]
        next_stop = self.stops[next_stop_id]
        
        bus["x"] = next_stop.x
        bus["y"] = next_stop.y
        bus["stuck_counter"] = 0
        bus["last_position"] = (next_stop.x, next_stop.y)
        bus["grid_route"] = []  # Clear route
        bus["route_index"] = 0
        
        # Process arrival
        self._process_bus_arrival(bus_id, next_stop_id)
        bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
        bus["current_stop"] = next_stop_id
    
    def _process_bus_arrival(self, bus_id: int, stop_id: str):
        """Process bus arrival at stop"""
        bus = self.buses[bus_id]
        stop_passengers = self.passengers[stop_id]
        
        # DROP OFF PASSENGERS
        passengers_to_drop = []
        for passenger in bus.get("passengers", []):
            if passenger["destination"] == stop_id:
                passengers_to_drop.append(passenger)
        
        # Remove dropped passengers from bus
        for passenger in passengers_to_drop:
            bus["passengers"].remove(passenger)
            bus["load"] -= 1
        
        # ALTERNATIVE DROP-OFF: If no passengers match destination, drop off some randomly
        if len(passengers_to_drop) == 0 and len(bus.get("passengers", [])) > 0:
            # Drop off 1-2 passengers randomly to prevent overcrowding
            num_to_drop = min(2, len(bus.get("passengers", [])))
            for i in range(num_to_drop):
                if bus.get("passengers", []):
                    passenger = bus["passengers"].pop(0)
                    bus["load"] -= 1
        
        # Pick up passengers
        passengers_to_pickup = []
        pickup_limit = min(5, bus["capacity"] - bus["load"])  # Limit pickup rate
        
        for i, passenger in enumerate(stop_passengers["waiting"][:pickup_limit]):
            if bus["load"] < bus["capacity"]:
                passengers_to_pickup.append(passenger)
                stop_passengers["waiting"].remove(passenger)
                bus["load"] += 1
        
        # Add picked up passengers to bus
        if not bus.get("passengers"):
            bus["passengers"] = []
        bus["passengers"].extend(passengers_to_pickup)
        
        # Update stop queue
        stop_passengers["queue_length"] = len(stop_passengers["waiting"])
    
    def update_wait_times(self):
        """Update passenger wait times"""
        for stop_id, stop_passengers in self.passengers.items():
            for passenger in stop_passengers["waiting"]:
                passenger["wait_time"] += 1
            
            # Update total wait time
            stop_passengers["total_wait_time"] = sum(p["wait_time"] for p in stop_passengers["waiting"])
    
    def step(self):
        """Perform one simulation step"""
        self.simulation_time += 1
        
        # Generate new passengers
        self.generate_passengers()
        
        # Move buses
        self.move_buses()
        
        # Update wait times
        self.update_wait_times()
    
    def get_system_state(self) -> Dict[str, Any]:
        """Get current system state for UI"""
        # Calculate KPIs
        total_wait_time = sum(stop["total_wait_time"] for stop in self.passengers.values())
        total_passengers = sum(len(stop["waiting"]) for stop in self.passengers.values())
        avg_wait_time = total_wait_time / max(1, total_passengers)
        
        # Bus loads
        bus_loads = [bus["load"] for bus in self.buses.values()]
        load_std = np.std(bus_loads) if bus_loads else 0
        
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
                    "status": bus["status"],
                    "grid_route": bus["grid_route"][:5] if bus["grid_route"] else []  # Show next 5 steps
                }
                for bus in self.buses.values()
            ],
            "stops": [
                {
                    "id": stop_id,
                    "x": stop.x,
                    "y": stop.y,
                    "name": stop.stop_name,
                    "queue_length": self.passengers[stop_id]["queue_length"],
                    "total_wait_time": self.passengers[stop_id]["total_wait_time"],
                    "routes": stop.routes
                }
                for stop_id, stop in self.stops.items()
            ],
            "kpis": {
                "avg_wait_time": avg_wait_time,
                "total_passengers": total_passengers,
                "load_std": load_std,
                "efficiency": 1.0 - (avg_wait_time / 1000) if avg_wait_time > 0 else 1.0
            },
            "routes": [
                {
                    "route_id": route.route_id,
                    "route_name": route.route_name,
                    "color": route.color,
                    "direction": route.direction
                }
                for route in self.routes.values()
            ]
        }

# FastAPI App
app = FastAPI(title="Manhattan Bus Dispatch System - Grid Routes")

# Global system instance
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    """Initialize the Manhattan bus system"""
    global manhattan_system
    print("🗽 Initializing Manhattan Bus Dispatch System with Grid Routes...")
    manhattan_system = ManhattanBusDispatchSystem()
    print("✅ Manhattan system with grid routes initialized successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Shutting down Manhattan Bus Dispatch System...")

@app.get("/", response_class=HTMLResponse)
async def get_manhattan_dashboard():
    """Serve the Manhattan bus dispatch dashboard with grid route visualization"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Manhattan Bus Dispatch — Grid Routes</title>
  <link href="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.css" rel="stylesheet" />
  <style>
    html, body { height:100%; margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
    #app { display:flex; height:100%; }
    #sidebar {
      width: 320px; background:#f7f4ef; border-right:1px solid #e5ded3; padding:16px; box-sizing:border-box;
      display:flex; flex-direction:column; gap:12px;
    }
    #map { flex:1; }
    h1 { margin:0 0 6px; font-size:20px; letter-spacing:.3px; }
    .muted { color:#6b6257; font-size:13px; }
    .panel { background:#fff; border:1px solid #e5ded3; border-radius:10px; padding:12px; }
    label { font-size:13px; color:#5a5248; }
    input[type="text"] { width:100%; padding:8px 10px; border:1px solid #d9d2c6; border-radius:8px; }
    button { padding:8px 10px; border:1px solid #d9d2c6; background:#fff; border-radius:8px; cursor:pointer; }
    button.primary { background:#0ea5e9; border-color:#0ea5e9; color:#fff; }
    .footer { margin-top:auto; font-size:12px; color:#8b8175; }
    .chip { display:inline-block; padding:2px 8px; border-radius:999px; background:#e8f4fb; color:#0b75a1; font-size:12px; margin:2px 4px 0 0; }
    .legend { position:absolute; top:12px; left:12px; background:#fff; padding:8px 10px; border-radius:8px; border:1px solid #e5ded3; }
    .status-indicator { position:absolute; top:12px; right:12px; background:#fff; padding:8px 10px; border-radius:8px; border:1px solid #e5ded3; }
    .kpi-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    .kpi-item { text-align:center; }
    .kpi-value { font-size:18px; font-weight:bold; color:#0ea5e9; }
    .kpi-label { font-size:11px; color:#6b6257; }
    .grid-info { font-size:11px; color:#6b6257; margin-top:4px; }
  </style>
</head>
<body>
<div id="app">
  <div id="sidebar">
    <div>
      <h1>Manhattan Bus Dispatch</h1>
      <div class="muted">Grid route following simulation</div>
    </div>

    <div class="panel">
      <label>System Status</label>
      <div id="connection-status" class="muted">🔴 Connecting...</div>
      <div style="margin-top:8px; display:flex; gap:8px;">
        <button id="static-btn">Static Routes</button>
        <button id="rl-btn" class="primary">RL Dispatch</button>
      </div>
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
          <div id="efficiency" class="kpi-value">0%</div>
          <div class="kpi-label">Efficiency</div>
        </div>
        <div class="kpi-item">
          <div id="load-balance" class="kpi-value">0.0</div>
          <div class="kpi-label">Load Balance</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <label>Grid Route Info</label>
      <div class="grid-info">
        Buses follow Manhattan street grid:<br/>
        • Avenues (north-south)<br/>
        • Streets (east-west)<br/>
        • Realistic routing patterns
      </div>
    </div>

    <div class="panel">
      <label>Route Filter</label>
      <input id="routeFilter" type="text" placeholder="e.g. M15 or M15|M101" />
      <div class="muted">Use | to include multiple. Leave empty to show all.</div>
    </div>

    <div class="panel">
      <label>Stress Testing</label>
      <div style="display:flex; flex-direction:column; gap:4px;">
        <button onclick="applyStress('closure')">🚧 Road Closure</button>
        <button onclick="applyStress('traffic')">🚗 Traffic Jam</button>
        <button onclick="applyStress('surge')">👥 Demand Surge</button>
      </div>
    </div>

    <div class="panel">
      <div><span class="chip">Grid routes</span> <span class="chip">Realistic movement</span></div>
      <div style="margin-top:8px; display:flex; gap:8px;">
        <button id="fitManhattan">Fit to Manhattan</button>
        <button id="resetView">Reset View</button>
      </div>
    </div>

    <div class="footer">
      Basemap © CARTO / OSM · Built with MapLibre GL
    </div>
  </div>
  <div id="map"></div>
</div>

<div class="legend">
  <div>🚌 Bus Stops • 🚌 Buses • Grid Routes • Click for details</div>
</div>
<div class="status-indicator">
  <div id="system-status">System: Loading...</div>
  <div id="bus-count">Buses: 0</div>
</div>

<script src="https://unpkg.com/maplibre-gl@3.6.1/dist/maplibre-gl.js"></script>
<script>
  const map = new maplibregl.Map({
    container: 'map',
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [-73.9712, 40.7831],
    zoom: 11.5
  });
  map.addControl(new maplibregl.NavigationControl(), 'top-right');
  const bounds = [[-74.03, 40.68], [-73.90, 40.88]];

  let ws = null;
  let isConnected = false;
  let currentMode = 'rl';
  let systemState = null;

  function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8000/live');
    
    ws.onopen = () => {
      console.log('Connected to Manhattan system');
      isConnected = true;
      document.getElementById('connection-status').innerHTML = '🟢 Connected';
      document.getElementById('connection-status').className = 'muted';
    };
    
    ws.onmessage = (event) => {
      systemState = JSON.parse(event.data);
      updateDashboard();
    };
    
    ws.onclose = () => {
      console.log('Disconnected from Manhattan system');
      isConnected = false;
      document.getElementById('connection-status').innerHTML = '🔴 Disconnected';
      document.getElementById('connection-status').className = 'muted';
      setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  function updateDashboard() {
    if (!systemState) return;

    // Update KPIs
    document.getElementById('avg-wait').textContent = systemState.kpis.avg_wait_time.toFixed(1) + 's';
    document.getElementById('total-passengers').textContent = systemState.kpis.total_passengers;
    document.getElementById('efficiency').textContent = (systemState.kpis.efficiency * 100).toFixed(1) + '%';
    document.getElementById('load-balance').textContent = systemState.kpis.load_std.toFixed(1);

    // Update status
    document.getElementById('system-status').textContent = `System: ${systemState.simulation_time}s`;
    document.getElementById('bus-count').textContent = `Buses: ${systemState.buses.length}`;

    // Update map
    updateMap();
  }

  function updateMap() {
    if (!systemState) return;

    // Update bus stops
    const stopsData = {
      type: "FeatureCollection",
      features: systemState.stops.map(stop => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [-73.9712 + (stop.x - 50) * 0.001, 40.7831 + (stop.y - 50) * 0.001]
        },
        properties: {
          stop_id: stop.id,
          stop_name: stop.name,
          routes_served_csv: stop.routes.join('|'),
          queue_length: stop.queue_length
        }
      }))
    };

    if (map.getSource('stops')) {
      map.getSource('stops').setData(stopsData);
    } else {
      map.addSource('stops', {
        type: 'geojson',
        data: stopsData,
        cluster: true,
        clusterMaxZoom: 13,
        clusterRadius: 40
      });

      // Add clustering layers
      map.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'stops',
        filter: ['has', 'point_count'],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['get', 'point_count'], 10, 12, 200, 28],
          'circle-color': '#0ea5e9',
          'circle-opacity': 0.9
        }
      });

      map.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'stops',
        filter: ['has', 'point_count'],
        layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 },
        paint: { 'text-color': '#fff' }
      });

      // Add stop circles
      map.addLayer({
        id: 'stops-circle',
        type: 'circle',
        source: 'stops',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 3, 15, 6],
          'circle-color': [
            'case',
            ['>', ['get', 'queue_length'], 5], '#ef4444',
            ['>', ['get', 'queue_length'], 2], '#f59e0b',
            '#10b981'
          ],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 1
        }
      });

      // Add stop labels
      map.addLayer({
        id: 'stops-label',
        type: 'symbol',
        source: 'stops',
        minzoom: 14,
        filter: ['!', ['has', 'point_count']],
        layout: {
          'text-field': ['get', 'stop_name'],
          'text-size': 10,
          'text-offset': [0, 1.5],
          'text-anchor': 'top'
        },
        paint: { 'text-color': '#2b2b2b', 'text-halo-color': '#ffffff', 'text-halo-width': 1 }
      });

      // Event handlers
      map.on('click', 'stops-circle', (e) => showPopup(e));
      map.on('click', 'stops-label', (e) => showPopup(e));
      map.on('mouseenter', 'stops-circle', () => map.getCanvas().style.cursor = 'pointer');
      map.on('mouseleave', 'stops-circle', () => map.getCanvas().style.cursor = '');
    }

    // Update buses with grid routes
    const busesData = {
      type: "FeatureCollection",
      features: systemState.buses.map(bus => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [-73.9712 + (bus.x - 50) * 0.001, 40.7831 + (bus.y - 50) * 0.001]
        },
        properties: {
          bus_id: bus.id,
          route_id: bus.route_id,
          load: bus.load,
          capacity: bus.capacity,
          color: bus.color,
          grid_route: bus.grid_route
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
          'circle-radius': 8,
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
        paint: { 'text-color': '#ffffff', 'text-halo-color': '#000000', 'text-halo-width': 1 }
      });
    }

    // Draw grid routes for buses
    updateGridRoutes(systemState.buses);
  }

  function updateGridRoutes(buses) {
    // Remove existing route lines
    if (map.getSource('grid-routes')) {
      map.removeLayer('grid-routes');
      map.removeSource('grid-routes');
    }

    // Create route lines for buses with grid routes
    const routeFeatures = [];
    buses.forEach(bus => {
      if (bus.grid_route && bus.grid_route.length > 1) {
        const coordinates = bus.grid_route.map(step => [
          -73.9712 + (step[0] - 50) * 0.001,
          40.7831 + (step[1] - 50) * 0.001
        ]);
        
        routeFeatures.push({
          type: "Feature",
          geometry: {
            type: "LineString",
            coordinates: coordinates
          },
          properties: {
            bus_id: bus.id,
            route_id: bus.route_id,
            color: bus.color
          }
        });
      }
    });

    if (routeFeatures.length > 0) {
      map.addSource('grid-routes', {
        type: 'geojson',
        data: {
          type: "FeatureCollection",
          features: routeFeatures
        }
      });

      map.addLayer({
        id: 'grid-routes',
        type: 'line',
        source: 'grid-routes',
        paint: {
          'line-color': ['get', 'color'],
          'line-width': 2,
          'line-opacity': 0.7
        }
      });
    }
  }

  function showPopup(e) {
    const f = e.features[0];
    const p = f.properties;
    const routes = (p.routes_served_csv || '').split('|').filter(Boolean).join(', ');
    new maplibregl.Popup()
      .setLngLat(e.lngLat)
      .setHTML(`<strong>${p.stop_name || 'Stop'}</strong><br/>Routes: ${routes || '—'}<br/>Queue: ${p.queue_length || 0}<br/><small>ID: ${p.stop_id || ''}</small>`)
      .addTo(map);
  }

  function switchMode(mode) {
    currentMode = mode;
    
    // Update button styles
    document.getElementById('static-btn').className = mode === 'static' 
      ? 'primary' : '';
    
    document.getElementById('rl-btn').className = mode === 'rl' 
      ? 'primary' : '';

    // Send mode change to server
    fetch('/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode })
    }).catch(error => console.error('Error switching mode:', error));
  }

  function applyStress(type) {
    fetch('/stress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: type })
    }).catch(error => console.error('Error applying stress:', error));
  }

  function applyRouteFilter(routesExpr) {
    if (!routesExpr) {
      map.setFilter('stops-circle', ['!', ['has', 'point_count']]);
      map.setFilter('stops-label', ['all', ['!', ['has', 'point_count']], ['>=', ['zoom'], 14]]);
      return;
    }
    const tokens = routesExpr.split('|').map(s => s.trim()).filter(Boolean);
    const orClauses = tokens.map(t => ['in', t, ['split', ['get','routes_served_csv'], '|']]);
    const filter = ['all', ['!', ['has','point_count']], ['any'].concat(orClauses)];
    map.setFilter('stops-circle', filter);
    map.setFilter('stops-label', ['all', filter, ['>=', ['zoom'], 14]]);
  }

  // Event listeners
  document.getElementById('static-btn').addEventListener('click', () => switchMode('static'));
  document.getElementById('rl-btn').addEventListener('click', () => switchMode('rl'));
  document.getElementById('fitManhattan').addEventListener('click', () => {
    map.fitBounds(bounds, {padding: 30, duration: 500});
  });
  document.getElementById('resetView').addEventListener('click', () => {
    map.setCenter([-73.9712, 40.7831]);
    map.setZoom(11.5);
  });
  document.getElementById('routeFilter').addEventListener('input', (ev) => {
    applyRouteFilter(ev.target.value);
  });

  // Initialize
  map.on('load', () => {
    connectWebSocket();
  });
</script>
</body>
</html>
    """

@app.get("/status")
async def get_status():
    """Get system status"""
    if not manhattan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    state = manhattan_system.get_system_state()
    return {
        "status": "running",
        "mode": manhattan_system.mode,
        "simulation_time": state["simulation_time"],
        "buses": len(state["buses"]),
        "stops": len(state["routes"]),
        "routes": len(state["routes"])
    }

@app.post("/mode")
async def switch_mode(request: dict):
    """Switch between static and RL mode"""
    if not manhattan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    mode = request.get("mode", "rl")
    manhattan_system.mode = mode
    return {"mode": mode, "message": f"Switched to {mode} mode"}

@app.post("/stress")
async def apply_stress(request: dict):
    """Apply stress to the system"""
    if not manhattan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    stress_type = request.get("type", "closure")
    return {"stress": stress_type, "message": f"Applied {stress_type} stress"}

@app.post("/reset")
async def reset_simulation(request: dict = None):
    """Reset the simulation"""
    if not manhattan_system:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    # Reinitialize system
    manhattan_system._initialize_system()
    return {"message": "Simulation reset"}

@app.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for live data streaming"""
    await websocket.accept()
    
    try:
        while True:
            if manhattan_system:
                # Step simulation
                manhattan_system.step()
                
                # Get system state
                state = manhattan_system.get_system_state()
                
                # Send to client
                await websocket.send_json(state)
            
            await asyncio.sleep(0.1)  # 10 Hz update rate
            
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    print("🗽 STARTING MANHATTAN BUS DISPATCH SYSTEM - GRID ROUTES")
    print("=" * 60)
    print("🗺️ MapLibre GL JS Map with Grid Routes")
    print("📍 Real Manhattan Street Grid")
    print("🎯 Realistic Bus Movement")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
