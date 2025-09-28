#!/usr/bin/env python3
"""
Manhattan Bus Dispatch System with RL
Realistic bus dispatch simulation using trained RL model for dynamic routing
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

class SimpleRLAgent:
    """Simple RL agent for bus dispatch"""
    
    def __init__(self, observation_space_size: int, action_space_size: int):
        self.observation_space_size = observation_space_size
        self.action_space_size = action_space_size
        
        # Simple Q-learning parameters
        self.learning_rate = 0.1
        self.epsilon = 0.05  # Lower exploration for inference
        self.gamma = 0.9
        
        # Q-table
        self.q_table = {}
        
    def get_action(self, observation: np.ndarray) -> int:
        """Get action from observation"""
        # Convert observation to state key
        state_key = tuple(observation.astype(int))
        
        # Initialize Q-values if not seen before
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_space_size)
        
        # Epsilon-greedy action selection
        if random.random() < self.epsilon:
            return random.randint(0, self.action_space_size - 1)
        else:
            return np.argmax(self.q_table[state_key])
    
    def load_model(self, filepath: str):
        """Load trained model"""
        try:
            with open(filepath, 'r') as f:
                model_data = json.load(f)
            
            self.q_table = {eval(k): np.array(v) for k, v in model_data["q_table"].items()}
            self.observation_space_size = model_data["observation_space_size"]
            self.action_space_size = model_data["action_space_size"]
            self.learning_rate = model_data["learning_rate"]
            self.epsilon = model_data["epsilon"]
            self.gamma = model_data["gamma"]
            
            print(f"✅ Loaded RL model from {filepath}")
            return True
        except Exception as e:
            print(f"⚠️ Error loading RL model: {e}")
            return False

class ManhattanBusDispatchSystem:
    """Realistic Manhattan bus dispatch system with RL"""
    
    def __init__(self):
        self.parser = ManhattanDataParser()
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        self.mode = "rl"  # rl or static
        self.rl_agent = None
        
        # Load Manhattan data
        self._load_manhattan_data()
        self._initialize_system()
        self._load_rl_model()
    
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
                    "speed": 1.0,
                    "status": "moving",
                    "passengers": []
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
    
    def _load_rl_model(self):
        """Load trained RL model"""
        print("🤖 Loading RL model...")
        
        self.rl_agent = SimpleRLAgent(50, 4)  # observation_space_size, action_space_size
        
        if self.rl_agent.load_model("manhattan_rl_model.json"):
            print("✅ RL model loaded successfully!")
        else:
            print("⚠️ No RL model found, using random actions")
            self.mode = "static"
    
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
            if random.random() < demand * 0.1:  # 10% chance per time step
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
    
    def get_observation(self) -> np.ndarray:
        """Get current observation for RL agent"""
        obs = []
        
        # Bus states (position, load, status)
        for bus in self.buses.values():
            obs.extend([bus["x"], bus["y"], bus["load"], 1 if bus["status"] == "moving" else 0])
        
        # Stop states (queue length, demand)
        for stop_id, stop in self.stops.items():
            obs.extend([self.passengers[stop_id]["queue_length"], 
                       self.get_manhattan_demand(stop_id, (self.simulation_time // 3600) % 24)])
        
        # Pad to fixed size
        while len(obs) < 50:
            obs.append(0.0)
        
        return np.array(obs[:50], dtype=np.float32)
    
    def apply_rl_action(self, bus_id: int, action: int):
        """Apply RL action to a bus"""
        bus = self.buses[bus_id]
        
        if action == 0:  # Continue on route
            self._continue_on_route(bus_id)
        elif action == 1:  # Go to high demand stop
            self._go_to_high_demand(bus_id)
        elif action == 2:  # Skip low demand stop
            self._skip_low_demand(bus_id)
        elif action == 3:  # Hold at current location
            self._hold_bus(bus_id)
    
    def _continue_on_route(self, bus_id: int):
        """Continue following the assigned route"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        if bus["next_stop_index"] < len(route.stops):
            next_stop_id = route.stops[bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # Move towards next stop
            dx = next_stop.x - bus["x"]
            dy = next_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 2:  # Arrived at stop
                self._process_bus_arrival(bus_id, next_stop_id)
                bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
                bus["current_stop"] = next_stop_id
            else:
                # Move towards next stop
                bus["x"] += int(dx / max(1, distance) * bus["speed"])
                bus["y"] += int(dy / max(1, distance) * bus["speed"])
    
    def _go_to_high_demand(self, bus_id: int):
        """Route bus to highest demand stop (DYNAMIC ROUTING)"""
        bus = self.buses[bus_id]
        
        # Find highest demand stop
        max_demand = 0
        target_stop_id = None
        
        for stop_id, stop in self.stops.items():
            demand = self.passengers[stop_id]["queue_length"]
            if demand > max_demand:
                max_demand = demand
                target_stop_id = stop_id
        
        if target_stop_id:
            target_stop = self.stops[target_stop_id]
            
            # Move towards target stop (DYNAMIC ROUTING)
            dx = target_stop.x - bus["x"]
            dy = target_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 2:  # Arrived at stop
                self._process_bus_arrival(bus_id, target_stop_id)
                bus["current_stop"] = target_stop_id
            else:
                # Move towards target stop
                bus["x"] += int(dx / max(1, distance) * bus["speed"])
                bus["y"] += int(dy / max(1, distance) * bus["speed"])
    
    def _skip_low_demand(self, bus_id: int):
        """Skip low demand stops and go to next high demand stop"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        # Find next high demand stop on route
        for i in range(len(route.stops)):
            next_stop_id = route.stops[(bus["next_stop_index"] + i) % len(route.stops)]
            if self.passengers[next_stop_id]["queue_length"] > 2:  # High demand threshold
                bus["next_stop_index"] = (bus["next_stop_index"] + i) % len(route.stops)
                break
        
        self._continue_on_route(bus_id)
    
    def _hold_bus(self, bus_id: int):
        """Hold bus at current location"""
        bus = self.buses[bus_id]
        bus["status"] = "holding"
        # Bus stays at current position
    
    def _process_bus_arrival(self, bus_id: int, stop_id: str):
        """Process bus arrival at stop"""
        bus = self.buses[bus_id]
        stop_passengers = self.passengers[stop_id]
        
        # Drop off passengers
        passengers_to_drop = [p for p in bus.get("passengers", []) if p["destination"] == stop_id]
        for passenger in passengers_to_drop:
            bus["passengers"].remove(passenger)
            bus["load"] -= 1
        
        # Pick up passengers
        passengers_to_pickup = []
        for passenger in stop_passengers["waiting"][:]:
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
        
        if self.mode == "rl" and self.rl_agent:
            # Use RL for dynamic routing
            obs = self.get_observation()
            
            # Get actions for all buses
            for bus_id in self.buses.keys():
                action = self.rl_agent.get_action(obs)
                self.apply_rl_action(bus_id, action)
        else:
            # Use static routing
            self._static_routing()
        
        # Update wait times
        self.update_wait_times()
    
    def _static_routing(self):
        """Static routing (follow fixed routes)"""
        for bus_id, bus in self.buses.items():
            if bus["status"] != "moving":
                continue
            
            route = self.routes[bus["route_id"]]
            current_stop = bus["current_stop"]
            
            if not current_stop or bus["next_stop_index"] >= len(route.stops):
                # Reset to start of route
                bus["next_stop_index"] = 0
                bus["current_stop"] = route.stops[0]
                current_stop = route.stops[0]
            
            # Move towards next stop
            next_stop_id = route.stops[bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # Simple movement towards next stop
            dx = next_stop.x - bus["x"]
            dy = next_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 2:  # Arrived at stop
                self._process_bus_arrival(bus_id, next_stop_id)
                bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
                bus["current_stop"] = next_stop_id
            else:
                # Move towards next stop
                bus["x"] += int(dx / max(1, distance) * bus["speed"])
                bus["y"] += int(dy / max(1, distance) * bus["speed"])
    
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
app = FastAPI(title="Manhattan Bus Dispatch System with RL")

# Global system instance
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    """Initialize the Manhattan bus system"""
    global manhattan_system
    print("🗽 Initializing Manhattan Bus Dispatch System with RL...")
    manhattan_system = ManhattanBusDispatchSystem()
    print("✅ Manhattan RL system initialized successfully!")

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
    <title>Manhattan Bus Dispatch System with RL</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .manhattan-grid { background: linear-gradient(45deg, #f0f9ff 25%, #e0f2fe 25%, #e0f2fe 50%, #f0f9ff 50%, #f0f9ff 75%, #e0f2fe 75%); }
        .bus-marker { transition: all 0.3s ease; }
        .stop-marker { transition: all 0.3s ease; }
        .route-line { stroke-dasharray: 5,5; animation: dash 1s linear infinite; }
        @keyframes dash { to { stroke-dashoffset: -10; } }
    </style>
</head>
<body class="bg-gray-50">
    <div class="min-h-screen">
        <!-- Header -->
        <header class="bg-white shadow-sm border-b">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-4">
                    <div>
                        <h1 class="text-2xl font-bold text-gray-900">🗽 Manhattan Bus Dispatch with RL</h1>
                        <p class="text-sm text-gray-600">Dynamic Routing • Real MTA Data • AI-Powered Dispatch</p>
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
                                RL Dispatch
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </header>
        
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Manhattan Map -->
                <div class="lg:col-span-2">
                    <div class="bg-white rounded-xl shadow-sm border p-6">
                        <h3 class="text-lg font-semibold text-gray-900 mb-4">🗺️ Manhattan Bus Network (Dynamic Routing)</h3>
                        <div class="relative">
                            <svg id="manhattan-map" width="100%" height="500" class="manhattan-grid rounded-lg border">
                                <!-- Manhattan street grid -->
                                <g id="street-grid"></g>
                                
                                <!-- Bus routes -->
                                <g id="route-lines"></g>
                                
                                <!-- Bus stops -->
                                <g id="bus-stops"></g>
                                
                                <!-- Buses -->
                                <g id="buses"></g>
                            </svg>
                            
                            <!-- Legend -->
                            <div class="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-sm">
                                <h4 class="font-semibold text-sm text-gray-900 mb-2">Legend</h4>
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
                            
                            <!-- RL Status -->
                            <div class="absolute top-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-sm">
                                <h4 class="font-semibold text-sm text-gray-900 mb-2">RL Status</h4>
                                <div class="space-y-1 text-xs">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-green-500 rounded-full"></div>
                                        <span>Dynamic Routing Active</span>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
                                        <span>Demand-Responsive</span>
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
                console.log('Connected to Manhattan RL system');
                isConnected = true;
                document.getElementById('connection-status').innerHTML = '🟢 Connected';
                document.getElementById('connection-status').className = 'px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800';
            };
            
            ws.onmessage = (event) => {
                systemState = JSON.parse(event.data);
                updateDashboard();
            };
            
            ws.onclose = () => {
                console.log('Disconnected from Manhattan RL system');
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
            updateManhattanMap();
        }

        function updateManhattanMap() {
            const svg = document.getElementById('manhattan-map');
            const streetGrid = document.getElementById('street-grid');
            const routeLines = document.getElementById('route-lines');
            const busStops = document.getElementById('bus-stops');
            const buses = document.getElementById('buses');

            // Clear previous content
            streetGrid.innerHTML = '';
            routeLines.innerHTML = '';
            busStops.innerHTML = '';
            buses.innerHTML = '';

            // Draw street grid
            for (let i = 0; i < 20; i++) {
                const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line1.setAttribute('x1', i * 25);
                line1.setAttribute('y1', 0);
                line1.setAttribute('x2', i * 25);
                line1.setAttribute('y2', 500);
                line1.setAttribute('stroke', '#e5e7eb');
                line1.setAttribute('stroke-width', '1');
                streetGrid.appendChild(line1);

                const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                line2.setAttribute('x1', 0);
                line2.setAttribute('y1', i * 25);
                line2.setAttribute('x2', 500);
                line2.setAttribute('y2', i * 25);
                line2.setAttribute('stroke', '#e5e7eb');
                line2.setAttribute('stroke-width', '1');
                streetGrid.appendChild(line2);
            }

            // Draw bus stops
            systemState.stops.forEach(stop => {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', stop.x * 5);
                circle.setAttribute('cy', stop.y * 5);
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
                text.setAttribute('x', stop.x * 5);
                text.setAttribute('y', stop.y * 5 - 10);
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('class', 'text-xs font-medium fill-gray-700');
                text.textContent = stop.queue_length;
                busStops.appendChild(text);
            });

            // Draw buses
            systemState.buses.forEach(bus => {
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', bus.x * 5);
                circle.setAttribute('cy', bus.y * 5);
                circle.setAttribute('r', '6');
                circle.setAttribute('fill', bus.color);
                circle.setAttribute('stroke', '#fff');
                circle.setAttribute('stroke-width', '2');
                circle.setAttribute('class', 'bus-marker');
                buses.appendChild(circle);

                // Add load text
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', bus.x * 5);
                text.setAttribute('y', bus.y * 5 + 3);
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
        "stops": len(state["stops"]),
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
    # TODO: Implement stress effects
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
    print("🗽 STARTING MANHATTAN BUS DISPATCH SYSTEM WITH RL")
    print("=" * 50)
    print("🚌 Dynamic Routing with RL")
    print("📍 Real Manhattan Stops & Routes")
    print("🎯 Demand-Responsive Dispatch")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
