from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import numpy as np
import sys
import os
import random
import time

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'env'))

from env.wrappers import BusDispatchEnv

app = FastAPI(title="Bus Dispatch RL Demo")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
simulation_env = None
current_mode = "static"
connected_clients = set()
simulation_time = 0.0

class ModeRequest(BaseModel):
    mode: str

class StressRequest(BaseModel):
    type: str
    params: dict = {}

@app.get("/")
async def dashboard():
    """Serve the dashboard"""
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bus Dispatch RL Demo</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100">
        <div class="min-h-screen p-6">
            <div class="max-w-7xl mx-auto">
                <!-- Header -->
                <div class="flex justify-between items-center mb-6">
                    <h1 class="text-3xl font-bold text-gray-900">Bus Dispatch RL Demo</h1>
                    <div class="flex items-center gap-4">
                        <div id="connection-status" class="flex items-center gap-2 px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
                            <div class="w-2 h-2 rounded-full bg-green-500"></div>
                            Connected
                        </div>
                        <div class="text-sm text-gray-600">
                            Time: <span id="time">0.0</span>m | Mode: <span id="mode">static</span>
                        </div>
                    </div>
                </div>
                
                <!-- Mode Controls -->
                <div class="bg-white rounded-lg shadow p-4 mb-6">
                    <div class="flex items-center gap-4">
                        <span class="text-lg font-semibold">Operation Mode:</span>
                        <button onclick="switchMode('static')" class="px-4 py-2 rounded-lg font-medium bg-blue-500 text-white">Static Schedule</button>
                        <button onclick="switchMode('rl')" class="px-4 py-2 rounded-lg font-medium bg-gray-200 text-gray-700">RL Policy</button>
                    </div>
                </div>
                
                <!-- KPI Cards -->
                <div class="grid grid-cols-4 gap-4 mb-6">
                    <div class="bg-white rounded-lg shadow p-4">
                        <h4 class="text-sm font-medium text-gray-600 mb-2">RL Avg Wait (min)</h4>
                        <div class="text-2xl font-bold text-gray-900" id="rl-wait">0.0</div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-4">
                        <h4 class="text-sm font-medium text-gray-600 mb-2">Baseline Avg Wait (min)</h4>
                        <div class="text-2xl font-bold text-gray-900" id="baseline-wait">0.0</div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-4">
                        <h4 class="text-sm font-medium text-gray-600 mb-2">RL Load Std</h4>
                        <div class="text-2xl font-bold text-gray-900" id="rl-load">0.0</div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-4">
                        <h4 class="text-sm font-medium text-gray-600 mb-2">Baseline Load Std</h4>
                        <div class="text-2xl font-bold text-gray-900" id="baseline-load">0.0</div>
                    </div>
                </div>
                
                <!-- Maps -->
                <div class="grid grid-cols-2 gap-6 mb-6">
                    <div class="bg-white rounded-lg shadow p-4">
                        <h3 class="text-lg font-semibold mb-3 text-center">Static Schedule (Baseline)</h3>
                        <div id="static-map" class="relative bg-gray-50 border rounded" style="width: 320px; height: 320px; margin: 0 auto;"></div>
                    </div>
                    <div class="bg-white rounded-lg shadow p-4">
                        <h3 class="text-lg font-semibold mb-3 text-center">RL Policy (Adaptive)</h3>
                        <div id="rl-map" class="relative bg-gray-50 border rounded" style="width: 320px; height: 320px; margin: 0 auto;"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let systemState = null;
            let ws = null;

            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:8000/live');
                
                ws.onopen = () => {
                    console.log('WebSocket connected');
                };
                
                ws.onmessage = (event) => {
                    systemState = JSON.parse(event.data);
                    updateDashboard();
                };
                
                ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    setTimeout(connectWebSocket, 3000);
                };
            }

            function updateDashboard() {
                if (!systemState) return;
                
                // Update time and mode
                document.getElementById('time').textContent = systemState.time ? systemState.time.toFixed(1) : '0.0';
                document.getElementById('mode').textContent = systemState.mode || 'static';
                
                // Update KPIs
                if (systemState.kpi) {
                    document.getElementById('rl-wait').textContent = systemState.kpi.avg_wait ? systemState.kpi.avg_wait.toFixed(1) : '0.0';
                    document.getElementById('rl-load').textContent = systemState.kpi.load_std ? systemState.kpi.load_std.toFixed(1) : '0.0';
                }
                
                if (systemState.baseline_kpi) {
                    document.getElementById('baseline-wait').textContent = systemState.baseline_kpi.avg_wait ? systemState.baseline_kpi.avg_wait.toFixed(1) : '0.0';
                    document.getElementById('baseline-load').textContent = systemState.baseline_kpi.load_std ? systemState.baseline_kpi.load_std.toFixed(1) : '0.0';
                }
                
                // Update maps - show same buses in both panels
                const allBuses = systemState.buses || [];
                updateMap('static-map', allBuses);
                updateMap('rl-map', allBuses); // Show same buses in both panels
            }
            
            function updateMap(containerId, buses) {
                const container = document.getElementById(containerId);
                container.innerHTML = '';
                
                if (!buses || buses.length === 0) {
                    container.innerHTML = '<div style="text-align: center; padding-top: 120px; color: #6b7280;">No buses</div>';
                    return;
                }
                
                // Create SVG for bus visualization
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('width', '320');
                svg.setAttribute('height', '320');
                svg.setAttribute('viewBox', '0 0 320 320');
                
                // Add grid lines
                for (let i = 0; i <= 20; i++) {
                    const line1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    line1.setAttribute('x1', i * 16);
                    line1.setAttribute('y1', 0);
                    line1.setAttribute('x2', i * 16);
                    line1.setAttribute('y2', 320);
                    line1.setAttribute('stroke', '#e5e7eb');
                    line1.setAttribute('stroke-width', '1');
                    svg.appendChild(line1);
                    
                    const line2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    line2.setAttribute('x1', 0);
                    line2.setAttribute('y1', i * 16);
                    line2.setAttribute('x2', 320);
                    line2.setAttribute('y2', i * 16);
                    line2.setAttribute('stroke', '#e5e7eb');
                    line2.setAttribute('stroke-width', '1');
                    svg.appendChild(line2);
                }
                
                // Add buses
                buses.forEach(bus => {
                    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                    rect.setAttribute('x', bus.x * 16 - 6);
                    rect.setAttribute('y', bus.y * 16 - 4);
                    rect.setAttribute('width', '12');
                    rect.setAttribute('height', '8');
                    rect.setAttribute('rx', '2');
                    rect.setAttribute('fill', bus.is_moving ? '#3b82f6' : '#6366f1');
                    rect.setAttribute('stroke', '#fff');
                    rect.setAttribute('stroke-width', '1');
                    svg.appendChild(rect);
                    
                    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                    text.setAttribute('x', bus.x * 16);
                    text.setAttribute('y', bus.y * 16 + 2);
                    text.setAttribute('font-size', '8');
                    text.setAttribute('text-anchor', 'middle');
                    text.setAttribute('fill', 'white');
                    text.setAttribute('font-weight', 'bold');
                    text.textContent = bus.id;
                    svg.appendChild(text);
                });
                
                container.appendChild(svg);
            }

            function switchMode(mode) {
                fetch('/mode', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({mode: mode})
                });
            }

            // Connect on page load
            connectWebSocket();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=dashboard_html)

@app.get("/status")
async def get_status():
    """Get system status"""
    return {
        "mode": current_mode,
        "rl_available": False,
        "running": True,
        "connected_clients": len(connected_clients),
        "simulation_time": simulation_time,
        "buses": 6,
        "stops": 32
    }

@app.get("/state")
async def get_state():
    """Get current system state"""
    # Generate some fake bus data for demonstration
    buses = []
    for i in range(6):
        buses.append({
            "id": i,
            "x": random.randint(0, 19),
            "y": random.randint(0, 19),
            "load": random.randint(0, 40),
            "capacity": 40,
            "next_stop": random.randint(100, 200),
            "is_moving": random.choice([True, False]),
            "mode": "static"
        })
    
    return {
        "time": simulation_time,
        "buses": buses,
        "stops": [{"id": i, "x": random.randint(0, 19), "y": random.randint(0, 19), "queue_len": random.randint(0, 10)} for i in range(32)],
        "kpi": {
            "avg_wait": random.uniform(5, 15),
            "load_std": random.uniform(0, 5)
        },
        "baseline_kpi": {
            "avg_wait": random.uniform(8, 20),
            "load_std": random.uniform(0, 8)
        }
    }

@app.post("/mode")
async def set_mode(request: ModeRequest):
    """Switch between static and RL modes"""
    global current_mode
    current_mode = request.mode
    return {"status": "success", "mode": current_mode}

@app.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    connected_clients.add(websocket)
    
    try:
        while True:
            # Send state update
            state = await get_state()
            await websocket.send_text(json.dumps(state))
            await asyncio.sleep(1)  # Update every second
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.on_event("startup")
async def startup_event():
    """Initialize the system"""
    global simulation_time
    print("Starting Bus Dispatch Demo...")
    
    # Start simulation timer
    async def simulation_timer():
        global simulation_time
        while True:
            simulation_time += 0.5
            await asyncio.sleep(0.5)
    
    asyncio.create_task(simulation_timer())
    print("✓ System initialized successfully!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
