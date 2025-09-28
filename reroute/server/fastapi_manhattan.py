#!/usr/bin/env python3
"""
Manhattan Bus Dispatch System with Real MTA Data
Realistic bus dispatch simulation using actual Manhattan bus stops and routes
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

# Import environment components
try:
    from wrappers import BusDispatchEnv
    from bus import BusFleet
    from city import ManhattanGrid, Stop
    from riders import RiderGenerator, RiderQueue
    from reward import RewardCalculator
    from traffic import TrafficSimulator
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    print("Using fallback implementations...")

class ManhattanBusDispatchSystem:
    """Realistic Manhattan bus dispatch system with real MTA data"""
    
    def __init__(self):
        self.parser = ManhattanDataParser()
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        self.mode = "static"  # static or rl
        self.trained_model = None
        
        # Load Manhattan data
        self._load_manhattan_data()
        self._initialize_system()
    
    def _load_manhattan_data(self):
        """Load real Manhattan bus data"""
        print("🗽 Loading Manhattan bus data...")
        
        # Load stops and routes
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
                    "status": "moving"
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
    
    def move_buses(self):
        """Move buses along their routes"""
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
app = FastAPI(title="Manhattan Bus Dispatch System")

# Global system instance
manhattan_system = None

@app.on_event("startup")
async def startup_event():
    """Initialize the Manhattan bus system"""
    global manhattan_system
    print("🗽 Initializing Manhattan Bus Dispatch System...")
    manhattan_system = ManhattanBusDispatchSystem()
    print("✅ Manhattan system initialized successfully!")

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
    <title>Manhattan Bus Dispatch System</title>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://unpkg.com/recharts@2.8.0/umd/Recharts.js"></script>
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
    <div id="root"></div>
    
    <script type="text/babel">
        const { useState, useEffect, useRef } = React;
        const { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } = Recharts;
        
        function ManhattanBusDashboard() {
            const [systemState, setSystemState] = useState(null);
            const [isConnected, setIsConnected] = useState(false);
            const [mode, setMode] = useState('static');
            const [chartData, setChartData] = useState([]);
            const wsRef = useRef(null);
            
            const connectWebSocket = () => {
                const ws = new WebSocket('ws://localhost:8000/live');
                wsRef.current = ws;
                
                ws.onopen = () => {
                    console.log('Connected to Manhattan system');
                    setIsConnected(true);
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    setSystemState(data);
                    
                    // Update chart data
                    setChartData(prev => {
                        const newData = [...prev, {
                            time: data.simulation_time,
                            avg_wait: data.kpis.avg_wait_time,
                            passengers: data.kpis.total_passengers,
                            efficiency: data.kpis.efficiency * 100
                        }].slice(-50); // Keep last 50 points
                        return newData;
                    });
                };
                
                ws.onclose = () => {
                    console.log('Disconnected from Manhattan system');
                    setIsConnected(false);
                    setTimeout(connectWebSocket, 3000); // Reconnect after 3s
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            };
            
            useEffect(() => {
                connectWebSocket();
                return () => {
                    if (wsRef.current) {
                        wsRef.current.close();
                    }
                };
            }, []);
            
            const switchMode = async (newMode) => {
                try {
                    const response = await fetch('/mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: newMode })
                    });
                    if (response.ok) {
                        setMode(newMode);
                    }
                } catch (error) {
                    console.error('Error switching mode:', error);
                }
            };
            
            const applyStress = async (type) => {
                try {
                    await fetch('/stress', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ type: type })
                    });
                } catch (error) {
                    console.error('Error applying stress:', error);
                }
            };
            
            if (!systemState) {
                return (
                    <div className="min-h-screen flex items-center justify-center">
                        <div className="text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                            <h2 className="text-xl font-semibold text-gray-700">Loading Manhattan Bus System...</h2>
                            <p className="text-gray-500 mt-2">Connecting to real MTA data</p>
                        </div>
                    </div>
                );
            }
            
            return (
                <div className="min-h-screen bg-gray-50">
                    {/* Header */}
                    <header className="bg-white shadow-sm border-b">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                            <div className="flex justify-between items-center py-4">
                                <div>
                                    <h1 className="text-2xl font-bold text-gray-900">🗽 Manhattan Bus Dispatch</h1>
                                    <p className="text-sm text-gray-600">Real MTA Routes & Stops • RL vs Static Dispatch</p>
                                </div>
                                <div className="flex items-center space-x-4">
                                    <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                                        isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                    }`}>
                                        {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                                    </div>
                                    <div className="flex space-x-2">
                                        <button
                                            onClick={() => switchMode('static')}
                                            className={`px-4 py-2 rounded-lg text-sm font-medium ${
                                                mode === 'static' 
                                                    ? 'bg-blue-600 text-white' 
                                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                            }`}
                                        >
                                            Static
                                        </button>
                                        <button
                                            onClick={() => switchMode('rl')}
                                            className={`px-4 py-2 rounded-lg text-sm font-medium ${
                                                mode === 'rl' 
                                                    ? 'bg-green-600 text-white' 
                                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                            }`}
                                        >
                                            RL Dispatch
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </header>
                    
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            {/* Manhattan Map */}
                            <div className="lg:col-span-2">
                                <div className="bg-white rounded-xl shadow-sm border p-6">
                                    <h3 className="text-lg font-semibold text-gray-900 mb-4">🗺️ Manhattan Bus Network</h3>
                                    <div className="relative">
                                        <svg width="100%" height="500" className="manhattan-grid rounded-lg border">
                                            {/* Manhattan street grid */}
                                            {Array.from({length: 20}, (_, i) => (
                                                <g key={i}>
                                                    <line x1={i * 25} y1={0} x2={i * 25} y2={500} stroke="#e5e7eb" strokeWidth="1"/>
                                                    <line x1={0} y1={i * 25} x2={500} y2={i * 25} stroke="#e5e7eb" strokeWidth="1"/>
                                                </g>
                                            ))}
                                            
                                            {/* Bus stops */}
                                            {systemState.stops.map(stop => (
                                                <g key={stop.id}>
                                                    <circle
                                                        cx={stop.x * 5}
                                                        cy={stop.y * 5}
                                                        r={Math.max(3, Math.min(8, stop.queue_length + 2))}
                                                        fill={stop.queue_length > 5 ? '#ef4444' : stop.queue_length > 2 ? '#f59e0b' : '#10b981'}
                                                        stroke="#fff"
                                                        strokeWidth="2"
                                                        className="stop-marker"
                                                    />
                                                    <text
                                                        x={stop.x * 5}
                                                        y={stop.y * 5 - 10}
                                                        textAnchor="middle"
                                                        className="text-xs font-medium fill-gray-700"
                                                    >
                                                        {stop.queue_length}
                                                    </text>
                                                </g>
                                            ))}
                                            
                                            {/* Bus routes */}
                                            {systemState.routes.map(route => (
                                                <g key={route.route_id}>
                                                    {systemState.stops
                                                        .filter(stop => stop.routes.includes(route.route_id))
                                                        .map((stop, idx, arr) => {
                                                            if (idx === 0) return null;
                                                            const prevStop = arr[idx - 1];
                                                            return (
                                                                <line
                                                                    key={`${route.route_id}-${idx}`}
                                                                    x1={prevStop.x * 5}
                                                                    y1={prevStop.y * 5}
                                                                    x2={stop.x * 5}
                                                                    y2={stop.y * 5}
                                                                    stroke={route.color}
                                                                    strokeWidth="2"
                                                                    strokeOpacity="0.6"
                                                                    className="route-line"
                                                                />
                                                            );
                                                        })
                                                    }
                                                </g>
                                            ))}
                                            
                                            {/* Buses */}
                                            {systemState.buses.map(bus => (
                                                <g key={bus.id}>
                                                    <circle
                                                        cx={bus.x * 5}
                                                        cy={bus.y * 5}
                                                        r="6"
                                                        fill={bus.color}
                                                        stroke="#fff"
                                                        strokeWidth="2"
                                                        className="bus-marker"
                                                    />
                                                    <text
                                                        x={bus.x * 5}
                                                        y={bus.y * 5 + 3}
                                                        textAnchor="middle"
                                                        className="text-xs font-bold fill-white"
                                                    >
                                                        {bus.load}
                                                    </text>
                                                </g>
                                            ))}
                                        </svg>
                                        
                                        {/* Legend */}
                                        <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg p-3 shadow-sm">
                                            <h4 className="font-semibold text-sm text-gray-900 mb-2">Legend</h4>
                                            <div className="space-y-1 text-xs">
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                                    <span>Low demand (0-2)</span>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                                                    <span>Medium demand (3-5)</span>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                                                    <span>High demand (6+)</span>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                                                    <span>Buses (load shown)</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            {/* KPIs and Controls */}
                            <div className="space-y-6">
                                {/* KPIs */}
                                <div className="bg-white rounded-xl shadow-sm border p-6">
                                    <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Performance</h3>
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm text-gray-600">Avg Wait Time</span>
                                            <span className="text-lg font-semibold text-blue-600">
                                                {systemState.kpis.avg_wait_time.toFixed(1)}s
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm text-gray-600">Total Passengers</span>
                                            <span className="text-lg font-semibold text-green-600">
                                                {systemState.kpis.total_passengers}
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm text-gray-600">System Efficiency</span>
                                            <span className="text-lg font-semibold text-purple-600">
                                                {(systemState.kpis.efficiency * 100).toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-sm text-gray-600">Load Balance</span>
                                            <span className="text-lg font-semibold text-orange-600">
                                                {systemState.kpis.load_std.toFixed(1)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                
                                {/* Stress Testing */}
                                <div className="bg-white rounded-xl shadow-sm border p-6">
                                    <h3 className="text-lg font-semibold text-gray-900 mb-4">⚡ Stress Testing</h3>
                                    <div className="space-y-2">
                                        <button
                                            onClick={() => applyStress('closure')}
                                            className="w-full px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                                        >
                                            🚧 Road Closure
                                        </button>
                                        <button
                                            onClick={() => applyStress('traffic')}
                                            className="w-full px-4 py-2 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 transition-colors"
                                        >
                                            🚗 Traffic Jam
                                        </button>
                                        <button
                                            onClick={() => applyStress('surge')}
                                            className="w-full px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
                                        >
                                            👥 Demand Surge
                                        </button>
                                    </div>
                                </div>
                                
                                {/* Performance Chart */}
                                <div className="bg-white rounded-xl shadow-sm border p-6">
                                    <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Performance Trends</h3>
                                    <div style={{ width: '100%', height: '200px' }}>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={chartData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="time" />
                                                <YAxis />
                                                <Tooltip />
                                                <Line type="monotone" dataKey="avg_wait" stroke="#3b82f6" strokeWidth={2} />
                                                <Line type="monotone" dataKey="efficiency" stroke="#10b981" strokeWidth={2} />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }
        
        ReactDOM.render(<ManhattanBusDashboard />, document.getElementById('root'));
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
    
    mode = request.get("mode", "static")
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
    print("🗽 STARTING MANHATTAN BUS DISPATCH SYSTEM")
    print("=" * 50)
    print("🚌 Real MTA Routes: M1, M2, M3, M4, M5, M7, M104, M14A, M14D, M15, M15SBS, M11")
    print("📍 Real Manhattan Stops: Times Square, Union Square, Central Park")
    print("🎯 Realistic Demand Patterns: Rush hour, off-peak, weekend")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
