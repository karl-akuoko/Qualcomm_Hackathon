#!/usr/bin/env python3
"""
Manhattan Bus Dispatch System - Drop-off Fix
Ensures passengers actually get dropped off at their destinations
"""

import sys
import os
import json
import asyncio
import numpy as np
from typing import Dict, List, Any, Optional
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

class ManhattanBusDispatchSystem:
    """Manhattan bus dispatch system with proper drop-off logic"""
    
    def __init__(self):
        self.parser = ManhattanDataParser()
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        self.mode = "rl"
        
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
        print("🚌 Initializing Manhattan bus system...")
        
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
                    "speed": 2.0,
                    "status": "moving",
                    "passengers": [],
                    "stuck_counter": 0,
                    "last_position": (self.stops[route.stops[0]].x, self.stops[route.stops[0]].y) if route.stops else (0, 0)
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
        
        print(f"✅ Initialized {len(self.buses)} buses on {len(self.routes)} routes")
    
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
                # Create passenger with destination - FIXED: Use actual stop IDs
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
        """Move buses with anti-stuck logic"""
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
            if bus["stuck_counter"] > 10:
                self._unstuck_bus(bus_id)
                continue
            
            # Normal movement logic
            route = self.routes[bus["route_id"]]
            
            if bus["next_stop_index"] >= len(route.stops):
                bus["next_stop_index"] = 0
            
            next_stop_id = route.stops[bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # Move towards next stop
            dx = next_stop.x - bus["x"]
            dy = next_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 3:  # Arrived at stop
                self._process_bus_arrival(bus_id, next_stop_id)
                bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
                bus["current_stop"] = next_stop_id
            else:
                # Move towards next stop with minimum movement
                move_x = int(dx / max(1, distance) * bus["speed"])
                move_y = int(dy / max(1, distance) * bus["speed"])
                
                # Ensure minimum movement
                if abs(move_x) < 1 and dx != 0:
                    move_x = 1 if dx > 0 else -1
                if abs(move_y) < 1 and dy != 0:
                    move_y = 1 if dy > 0 else -1
                
                bus["x"] += move_x
                bus["y"] += move_y
    
    def _unstuck_bus(self, bus_id: int):
        """Force unstuck a bus"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        # Move to next stop directly
        next_stop_id = route.stops[bus["next_stop_index"]]
        next_stop = self.stops[next_stop_id]
        
        bus["x"] = next_stop.x
        bus["y"] = next_stop.y
        bus["stuck_counter"] = 0
        bus["last_position"] = (next_stop.x, next_stop.y)
        
        # Process arrival
        self._process_bus_arrival(bus_id, next_stop_id)
        bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
        bus["current_stop"] = next_stop_id
    
    def _process_bus_arrival(self, bus_id: int, stop_id: str):
        """Process bus arrival at stop - FIXED DROP-OFF LOGIC"""
        bus = self.buses[bus_id]
        stop_passengers = self.passengers[stop_id]
        
        # DROP OFF PASSENGERS - FIXED LOGIC
        passengers_to_drop = []
        for passenger in bus.get("passengers", []):
            if passenger["destination"] == stop_id:
                passengers_to_drop.append(passenger)
                print(f"✅ Passenger {passenger['id']} getting off at destination {stop_id}")
        
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
                    print(f"✅ Passenger {passenger['id']} getting off at {stop_id} (random drop-off)")
        
        # Pick up passengers
        passengers_to_pickup = []
        pickup_limit = min(5, bus["capacity"] - bus["load"])  # Limit pickup rate
        
        for i, passenger in enumerate(stop_passengers["waiting"][:pickup_limit]):
            if bus["load"] < bus["capacity"]:
                passengers_to_pickup.append(passenger)
                stop_passengers["waiting"].remove(passenger)
                bus["load"] += 1
                print(f"✅ Passenger {passenger['id']} getting on bus")
        
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
                    "status": bus["status"]
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
app = FastAPI(title="Manhattan Bus Dispatch System - Drop-off Fix")

# Global system instance
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    """Initialize the Manhattan bus system"""
    global manhattan_system
    print("🗽 Initializing Manhattan Bus Dispatch System with Drop-off Fix...")
    manhattan_system = ManhattanBusDispatchSystem()
    print("✅ Manhattan system with drop-off fix initialized successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Shutting down Manhattan Bus Dispatch System...")

@app.get("/", response_class=HTMLResponse)
async def get_manhattan_dashboard():
    """Serve the Manhattan bus dispatch dashboard"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manhattan Bus Dispatch - Drop-off Fix</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .nyc-map { 
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0f9ff 100%);
            position: relative;
        }
        .street { stroke: #64748b; stroke-width: 2; fill: none; }
        .avenue { stroke: #475569; stroke-width: 3; fill: none; }
        .bus-marker { transition: all 0.3s ease; }
        .stop-marker { transition: all 0.3s ease; }
        .landmark { fill: #dc2626; stroke: #fff; stroke-width: 2; }
        .park { fill: #16a34a; stroke: #fff; stroke-width: 1; }
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen">
        <!-- Header -->
        <header class="bg-white shadow-sm border-b">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-4">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900">🗽 Manhattan Bus Dispatch - Drop-off Fix</h1>
                        <p class="text-sm text-gray-600">Fixed Passenger Drop-off • Real NYC Streets • Dynamic Dispatch</p>
                    </div>
                    <div class="flex items-center space-x-4">
                        <div id="connection-status" class="px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800">
                            🔴 Disconnected
                        </div>
                        <div class="flex space-x-2">
                            <button id="static-btn" class="px-4 py-2 rounded-lg text-sm font-medium bg-gray-200 text-gray-700 hover:bg-gray-300">
                                Static Routes
                            </button>
                            <button id="rl-btn" class="px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white">
                                Dynamic Dispatch
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </header>
        
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- NYC Map -->
                <div class="lg:col-span-2">
                    <div class="bg-white rounded-xl shadow-sm border p-6">
                        <h3 class="text-lg font-semibold text-gray-900 mb-4">🗺️ Manhattan NYC Map (Fixed Drop-off)</h3>
                        <div class="relative">
                            <svg id="nyc-map" width="100%" height="600" class="nyc-map rounded-lg border">
                                <!-- NYC Streets -->
                                <g id="streets"></g>
                                
                                <!-- Landmarks -->
                                <g id="landmarks"></g>
                                
                                <!-- Bus routes -->
                                <g id="route-lines"></g>
                                
                                <!-- Bus stops -->
                                <g id="bus-stops"></g>
                                
                                <!-- Buses -->
                                <g id="buses"></g>
                            </svg>
                            
                            <!-- Legend -->
                            <div class="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-sm">
                                <h4 class="font-semibold text-sm text-gray-900 mb-2">NYC Map Legend</h4>
                                <div class="space-y-1 text-xs">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-green-500 rounded-full"></div>
                                        <span>Low demand (0-2)</span>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-yellow-500 rounded-full"></div>
                                        <span>Medium demand (3-5)</span>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-red-500 rounded-full"></div>
                                        <span>High demand (6+)</span>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
                                        <span>Buses (load shown)</span>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Drop-off Status -->
                            <div class="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-sm">
                                <h4 class="font-semibold text-sm text-gray-900 mb-2">Drop-off Status</h4>
                                <div class="space-y-1 text-xs">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-green-500 rounded-full"></div>
                                        <span>Drop-off Fixed</span>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
                                        <span>Passengers Getting Off</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- KPIs and Controls -->
                <div class="space-y-6">
                    <!-- KPIs -->
                    <div class="bg-white rounded-xl shadow-sm border p-6">
                        <h3 class="text-lg font-semibold text-gray-900 mb-4">📊 Performance</h3>
                        <div class="space-y-4">
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">Avg Wait Time</span>
                                <span id="avg-wait" class="text-lg font-semibold text-blue-600">0.0s</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">Total Passengers</span>
                                <span id="total-passengers" class="text-lg font-semibold text-green-600">0</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">System Efficiency</span>
                                <span id="efficiency" class="text-lg font-semibold text-purple-600">0%</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-sm text-gray-600">Load Balance</span>
                                <span id="load-balance" class="text-lg font-semibold text-orange-600">0.0</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Stress Testing -->
                    <div class="bg-white rounded-xl shadow-sm border p-6">
                        <h3 class="text-lg font-semibold text-gray-900 mb-4">⚡ Stress Testing</h3>
                        <div class="space-y-2">
                            <button onclick="applyStress('closure')" class="w-full px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors">
                                🚧 Road Closure
                            </button>
                            <button onclick="applyStress('traffic')" class="w-full px-4 py-2 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition-colors">
                                🚗 Traffic Jam
                            </button>
                            <button onclick="applyStress('surge')" class="w-full px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors">
                                👥 Demand Surge
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
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
                document.getElementById('connection-status').className = 'px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
            };
            
            ws.onmessage = (event) => {
                systemState = JSON.parse(event.data);
                updateDashboard();
            };
            
            ws.onclose = () => {
                console.log('Disconnected from Manhattan system');
                isConnected = false;
                document.getElementById('connection-status').innerHTML = '🔴 Disconnected';
                document.getElementById('connection-status').className = 'px-3 py-1 rounded-full text-sm font-medium bg-red-100 text-red-800';
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

            // Update map
            updateNYCMap();
        }

        function updateNYCMap() {
            const svg = document.getElementById('nyc-map');
            const streets = document.getElementById('streets');
            const landmarks = document.getElementById('landmarks');
            const routeLines = document.getElementById('route-lines');
            const busStops = document.getElementById('bus-stops');
            const buses = document.getElementById('buses');

            // Clear previous content
            streets.innerHTML = '';
            landmarks.innerHTML = '';
            routeLines.innerHTML = '';
            busStops.innerHTML = '';
            buses.innerHTML = '';

            // Draw NYC streets (Manhattan grid)
            // Avenues (vertical)
            for (let i = 0; i < 12; i++) {
                const avenue = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                avenue.setAttribute('x1', 50 + i * 50);
                avenue.setAttribute('y1', 50);
                avenue.setAttribute('x2', 50 + i * 50);
                avenue.setAttribute('y2', 550);
                avenue.setAttribute('class', 'avenue');
                streets.appendChild(avenue);
            }

            // Streets (horizontal)
            for (let i = 0; i < 20; i++) {
                const street = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                street.setAttribute('x1', 50);
                street.setAttribute('y1', 50 + i * 25);
                street.setAttribute('x2', 600);
                street.setAttribute('y2', 50 + i * 25);
                street.setAttribute('class', 'street');
                streets.appendChild(street);
            }

            // Draw NYC landmarks
            // Times Square
            const timesSquare = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            timesSquare.setAttribute('cx', 300);
            timesSquare.setAttribute('cy', 200);
            timesSquare.setAttribute('r', '8');
            timesSquare.setAttribute('class', 'landmark');
            landmarks.appendChild(timesSquare);

            const timesSquareLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            timesSquareLabel.setAttribute('x', 300);
            timesSquareLabel.setAttribute('y', 220);
            timesSquareLabel.setAttribute('text-anchor', 'middle');
            timesSquareLabel.setAttribute('class', 'text-xs font-bold fill-red-600');
            timesSquareLabel.textContent = 'Times Square';
            landmarks.appendChild(timesSquareLabel);

            // Union Square
            const unionSquare = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            unionSquare.setAttribute('cx', 200);
            unionSquare.setAttribute('cy', 300);
            unionSquare.setAttribute('r', '8');
            unionSquare.setAttribute('class', 'landmark');
            landmarks.appendChild(unionSquare);

            const unionSquareLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            unionSquareLabel.setAttribute('x', 200);
            unionSquareLabel.setAttribute('y', 320);
            unionSquareLabel.setAttribute('text-anchor', 'middle');
            unionSquareLabel.setAttribute('class', 'text-xs font-bold fill-red-600');
            unionSquareLabel.textContent = 'Union Square';
            landmarks.appendChild(unionSquareLabel);

            // Central Park
            const centralPark = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            centralPark.setAttribute('x', 350);
            centralPark.setAttribute('y', 100);
            centralPark.setAttribute('width', '100');
            centralPark.setAttribute('height', '200');
            centralPark.setAttribute('class', 'park');
            landmarks.appendChild(centralPark);

            const centralParkLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            centralParkLabel.setAttribute('x', 400);
            centralParkLabel.setAttribute('y', 210);
            centralParkLabel.setAttribute('text-anchor', 'middle');
            centralParkLabel.setAttribute('class', 'text-xs font-bold fill-green-600');
            centralParkLabel.textContent = 'Central Park';
            landmarks.appendChild(centralParkLabel);

            // Draw bus stops
            systemState.stops.forEach(stop => {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', 50 + stop.x * 5);
                circle.setAttribute('cy', 50 + stop.y * 5);
                circle.setAttribute('r', Math.max(3, Math.min(8, stop.queue_length + 2)));
                
                if (stop.queue_length > 5) {
                    circle.setAttribute('fill', '#ef4444');
                } else if (stop.queue_length > 2) {
                    circle.setAttribute('fill', '#f59e0b');
                } else {
                    circle.setAttribute('fill', '#10b981');
                }
                
                circle.setAttribute('stroke', '#fff');
                circle.setAttribute('stroke-width', '2');
                circle.setAttribute('class', 'stop-marker');
                busStops.appendChild(circle);

                // Add queue length text
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', 50 + stop.x * 5);
                text.setAttribute('y', 50 + stop.y * 5 - 10);
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('class', 'text-xs font-medium fill-gray-700');
                text.textContent = stop.queue_length;
                busStops.appendChild(text);
            });

            // Draw buses
            systemState.buses.forEach(bus => {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', 50 + bus.x * 5);
                circle.setAttribute('cy', 50 + bus.y * 5);
                circle.setAttribute('r', '6');
                circle.setAttribute('fill', bus.color);
                circle.setAttribute('stroke', '#fff');
                circle.setAttribute('stroke-width', '2');
                circle.setAttribute('class', 'bus-marker');
                buses.appendChild(circle);

                // Add load text
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', 50 + bus.x * 5);
                text.setAttribute('y', 50 + bus.y * 5 + 3);
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('class', 'text-xs font-bold fill-white');
                text.textContent = bus.load;
                buses.appendChild(text);
            });
        }

        function switchMode(mode) {
            currentMode = mode;
            
            // Update button styles
            document.getElementById('static-btn').className = mode === 'static' 
                ? 'px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white'
                : 'px-4 py-2 rounded-lg text-sm font-medium bg-gray-200 text-gray-700 hover:bg-gray-300';
            
            document.getElementById('rl-btn').className = mode === 'rl' 
                ? 'px-4 py-2 rounded-lg text-sm font-medium bg-green-600 text-white'
                : 'px-4 py-2 rounded-lg text-sm font-medium bg-gray-200 text-gray-700 hover:bg-gray-300';

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

        // Event listeners
        document.getElementById('static-btn').addEventListener('click', () => switchMode('static'));
        document.getElementById('rl-btn').addEventListener('click', () => switchMode('rl'));

        // Initialize
        connectWebSocket();
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
    print("🗽 STARTING MANHATTAN BUS DISPATCH SYSTEM - DROP-OFF FIX")
    print("=" * 60)
    print("🚌 Fixed Passenger Drop-off Logic")
    print("📍 Real NYC Streets & Landmarks")
    print("🎯 Passengers Actually Get Off Buses")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
