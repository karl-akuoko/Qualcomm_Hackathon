from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import numpy as np
import sys
import os
import time
from typing import Dict, List, Optional, Any

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'env'))
sys.path.append(os.path.join(parent_dir, 'rl'))

# Import environment
from env.wrappers import BusDispatchEnv
from env.bus import BusMode

# Pydantic models for API
class ModeRequest(BaseModel):
    mode: str  # "static" or "rl"

class StressRequest(BaseModel):
    type: str  # "closure", "traffic", "surge"
    params: Dict[str, Any] = {}

class ResetRequest(BaseModel):
    seed: int = 42

# Global simulation state
simulation_env = None
current_mode = "static"
is_running = False
websocket_connections = []
simulation_data = {
    "time": 0.0,
    "buses": [],
    "stops": [],
    "kpi": {"avg_wait": 0.0, "load_std": 0.0},
    "baseline_kpi": {"avg_wait": 0.0, "load_std": 0.0}
}

app = FastAPI(title="Bus Dispatch RL Mobile API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the mobile-optimized dashboard"""
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bus Dispatch RL - Mobile</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f8fafc; 
                color: #1f2937;
                overflow-x: hidden;
            }
            .container { max-width: 100vw; padding: 10px; }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 15px; 
                border-radius: 12px; 
                margin-bottom: 15px; 
                text-align: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .status { 
                padding: 8px 12px; 
                border-radius: 20px; 
                margin: 8px 0; 
                font-size: 14px;
                display: inline-block;
            }
            .status.connected { background: #10b981; color: white; }
            .status.disconnected { background: #ef4444; color: white; }
            .controls { 
                display: grid; 
                grid-template-columns: repeat(2, 1fr); 
                gap: 8px; 
                margin: 15px 0; 
            }
            .btn { 
                padding: 12px 8px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-weight: 600; 
                font-size: 12px;
                text-align: center;
                transition: all 0.2s;
            }
            .btn:active { transform: scale(0.95); }
            .btn-primary { background: #3b82f6; color: white; }
            .btn-success { background: #10b981; color: white; }
            .btn-danger { background: #ef4444; color: white; }
            .btn-warning { background: #f59e0b; color: white; }
            .btn-secondary { background: #6b7280; color: white; }
            .kpi-grid { 
                display: grid; 
                grid-template-columns: repeat(2, 1fr); 
                gap: 10px; 
                margin: 15px 0; 
            }
            .kpi-card { 
                background: white; 
                padding: 12px; 
                border-radius: 8px; 
                text-align: center; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border: 1px solid #e5e7eb;
            }
            .kpi-value { font-size: 20px; font-weight: bold; color: #1f2937; }
            .kpi-label { font-size: 11px; color: #6b7280; margin-top: 4px; }
            .map-container { 
                width: 100%; 
                height: 300px; 
                border: 2px solid #e5e7eb; 
                border-radius: 12px; 
                background: #f9fafb; 
                position: relative; 
                overflow: hidden;
                margin: 15px 0;
            }
            .grid-lines {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: none;
            }
            .grid-line {
                position: absolute;
                background: #e5e7eb;
            }
            .grid-line.horizontal {
                width: 100%;
                height: 1px;
            }
            .grid-line.vertical {
                height: 100%;
                width: 1px;
            }
            .bus { 
                position: absolute; 
                width: 16px; 
                height: 16px; 
                background: #3b82f6; 
                border-radius: 50%; 
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
                z-index: 10;
            }
            .bus.rl { background: #10b981; }
            .bus.static { background: #6b7280; }
            .stop { 
                position: absolute; 
                width: 12px; 
                height: 12px; 
                background: #f59e0b; 
                border-radius: 50%; 
                border: 2px solid white;
                box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                z-index: 5;
            }
            .stop::after {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                border: 2px solid #f59e0b;
                border-radius: 50%;
                opacity: 0.3;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { transform: scale(1); opacity: 0.3; }
                50% { transform: scale(1.2); opacity: 0.1; }
                100% { transform: scale(1); opacity: 0.3; }
            }
            .info-panel { 
                background: white; 
                padding: 12px; 
                border-radius: 8px; 
                margin: 10px 0; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border: 1px solid #e5e7eb;
            }
            .chart { 
                height: 150px; 
                background: white; 
                border-radius: 8px; 
                padding: 10px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border: 1px solid #e5e7eb;
            }
            .mobile-optimized { font-size: 14px; }
            @media (max-width: 768px) {
                .container { padding: 5px; }
                .controls { grid-template-columns: 1fr; }
                .kpi-grid { grid-template-columns: 1fr; }
                .btn { padding: 10px; font-size: 14px; }
            }
        </style>
    </head>
    <body>
        <div class="container mobile-optimized">
            <div class="header">
                <h1>🚌 Bus Dispatch RL</h1>
                <div id="status" class="status disconnected">Disconnected</div>
                <div>Time: <span id="time">0.0</span>m | Mode: <span id="mode">static</span></div>
            </div>
            
            <div class="info-panel">
                <h3>System Status</h3>
                <div id="system-info">Loading...</div>
            </div>
            
            <div class="controls">
                <button class="btn btn-primary" onclick="switchMode('static')">Static</button>
                <button class="btn btn-success" onclick="switchMode('rl')">RL Policy</button>
                <button class="btn btn-danger" onclick="applyStress('closure')">Road Closure</button>
                <button class="btn btn-warning" onclick="applyStress('traffic')">Traffic</button>
                <button class="btn btn-warning" onclick="applyStress('surge')">Surge</button>
                <button class="btn btn-secondary" onclick="resetSim()">Reset</button>
            </div>
            
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-value" id="rl-wait">0.0</div>
                    <div class="kpi-label">RL Wait (min)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value" id="baseline-wait">0.0</div>
                    <div class="kpi-label">Baseline Wait (min)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value" id="rl-load">0.0</div>
                    <div class="kpi-label">RL Load Std</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value" id="baseline-load">0.0</div>
                    <div class="kpi-label">Baseline Load Std</div>
                </div>
            </div>
            
            <div class="card">
                <h3>Manhattan Grid Simulation</h3>
                <div class="map-container" id="map">
                    <div class="grid-lines" id="grid-lines"></div>
                    <div style="text-align: center; padding-top: 120px; color: #6b7280;">
                        Loading simulation...
                    </div>
                </div>
            </div>
            
            <div class="info-panel">
                <h3>Performance</h3>
                <div class="chart" id="chart">
                    <div style="text-align: center; padding-top: 50px; color: #6b7280;">
                        Performance metrics will appear here...
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let systemState = null;
            let gridSize = 20;
            
            function createGrid() {
                const container = document.getElementById('map');
                const gridLines = document.getElementById('grid-lines');
                gridLines.innerHTML = '';
                
                // Create horizontal lines
                for (let i = 0; i <= gridSize; i++) {
                    const line = document.createElement('div');
                    line.className = 'grid-line horizontal';
                    line.style.top = (i * (300 / gridSize)) + 'px';
                    gridLines.appendChild(line);
                }
                
                // Create vertical lines
                for (let i = 0; i <= gridSize; i++) {
                    const line = document.createElement('div');
                    line.className = 'grid-line vertical';
                    line.style.left = (i * (300 / gridSize)) + 'px';
                    gridLines.appendChild(line);
                }
            }
            
            function connectWebSocket() {
                try {
                    ws = new WebSocket('ws://localhost:8000/live');
                    
                    ws.onopen = function() {
                        console.log('WebSocket connected');
                        document.getElementById('status').textContent = 'Connected';
                        document.getElementById('status').className = 'status connected';
                    };
                    
                    ws.onmessage = function(event) {
                        try {
                            systemState = JSON.parse(event.data);
                            updateDashboard();
                        } catch (error) {
                            console.error('Error parsing WebSocket message:', error);
                        }
                    };
                    
                    ws.onclose = function() {
                        console.log('WebSocket disconnected');
                        document.getElementById('status').textContent = 'Disconnected';
                        document.getElementById('status').className = 'status disconnected';
                        setTimeout(connectWebSocket, 3000);
                    };
                    
                    ws.onerror = function(error) {
                        console.error('WebSocket error:', error);
                    };
                } catch (error) {
                    console.error('Error creating WebSocket:', error);
                    setTimeout(connectWebSocket, 3000);
                }
            }
            
            function updateDashboard() {
                if (!systemState) return;
                
                // Update time and mode
                document.getElementById('time').textContent = systemState.time ? systemState.time.toFixed(1) : '0.0';
                
                // Update KPIs
                if (systemState.kpi) {
                    document.getElementById('rl-wait').textContent = systemState.kpi.avg_wait ? systemState.kpi.avg_wait.toFixed(1) : '0.0';
                    document.getElementById('rl-load').textContent = systemState.kpi.load_std ? systemState.kpi.load_std.toFixed(1) : '0.0';
                }
                
                if (systemState.baseline_kpi) {
                    document.getElementById('baseline-wait').textContent = systemState.baseline_kpi.avg_wait ? systemState.baseline_kpi.avg_wait.toFixed(1) : '0.0';
                    document.getElementById('baseline-load').textContent = systemState.baseline_kpi.load_std ? systemState.baseline_kpi.load_std.toFixed(1) : '0.0';
                }
                
                // Update map
                updateMap();
            }
            
            function updateMap() {
                const container = document.getElementById('map');
                
                // Remove existing buses and stops
                const existingBuses = container.querySelectorAll('.bus');
                const existingStops = container.querySelectorAll('.stop');
                existingBuses.forEach(el => el.remove());
                existingStops.forEach(el => el.remove());
                
                if (!systemState) return;
                
                // Add stops
                if (systemState.stops) {
                    systemState.stops.forEach(stop => {
                        const stopElement = document.createElement('div');
                        stopElement.className = 'stop';
                        stopElement.style.left = (stop.x * (300 / gridSize) - 6) + 'px';
                        stopElement.style.top = (stop.y * (300 / gridSize) - 6) + 'px';
                        stopElement.title = `Stop ${stop.id}: ${stop.queue_len} waiting`;
                        container.appendChild(stopElement);
                    });
                }
                
                // Add buses
                if (systemState.buses) {
                    systemState.buses.forEach(bus => {
                        const busElement = document.createElement('div');
                        busElement.className = `bus ${bus.mode}`;
                        busElement.style.left = (bus.x * (300 / gridSize) - 8) + 'px';
                        busElement.style.top = (bus.y * (300 / gridSize) - 8) + 'px';
                        busElement.title = `Bus ${bus.id}: ${bus.load}/${bus.capacity} passengers (${bus.mode})`;
                        container.appendChild(busElement);
                    });
                }
            }
            
            async function switchMode(mode) {
                try {
                    const response = await fetch('/mode', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode })
                    });
                    if (response.ok) {
                        document.getElementById('mode').textContent = mode;
                    }
                } catch (error) {
                    console.error('Error switching mode:', error);
                }
            }
            
            async function applyStress(type) {
                try {
                    await fetch('/stress', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ type, params: {} })
                    });
                } catch (error) {
                    console.error('Error applying stress:', error);
                }
            }
            
            async function resetSim() {
                try {
                    await fetch('/reset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ seed: 42 })
                    });
                } catch (error) {
                    console.error('Error resetting simulation:', error);
                }
            }
            
            // Initialize
            createGrid();
            connectWebSocket();
            
            // Fetch initial status
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('mode').textContent = data.mode || 'static';
                    document.getElementById('system-info').innerHTML = `
                        <strong>Buses:</strong> ${data.buses || 0} | 
                        <strong>Stops:</strong> ${data.stops || 0} | 
                        <strong>Clients:</strong> ${data.connected_clients || 0}
                    `;
                })
                .catch(error => console.error('Error fetching status:', error));
        </script>
    </body>
    </html>
    """
    return dashboard_html

@app.on_event("startup")
async def startup_event():
    """Initialize simulation environment"""
    global simulation_env
    
    print("Initializing Mobile Bus Dispatch System...")
    
    # Initialize environment with proper settings
    simulation_env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,  # 1 minute steps for mobile
        max_episode_time=float('inf'),
        seed=42
    )
    
    # Reset environment
    obs, info = simulation_env.reset()
    
    # Start simulation loop
    asyncio.create_task(simulation_loop())
    
    print("Mobile system initialized successfully!")

async def simulation_loop():
    """Simplified simulation loop for mobile"""
    global simulation_env, is_running, simulation_data
    
    is_running = True
    
    while is_running:
        try:
            # Get current observation
            obs = simulation_env._get_observation()
            
            # Generate simple actions (static mode)
            actions = [0] * simulation_env.num_buses  # CONTINUE action
            
            # Step environment
            obs, reward, done, truncated, info = simulation_env.step(np.array(actions))
            
            # Reset if episode ended
            if done or truncated:
                obs, info = simulation_env.reset()
            
            # Update simulation data
            simulation_data = simulation_env.get_system_state()
            
            # Broadcast state to WebSocket clients
            await broadcast_state()
            
            # Control simulation speed (1 Hz for mobile)
            await asyncio.sleep(1.0)
            
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            await asyncio.sleep(1.0)

async def broadcast_state():
    """Broadcast current system state to all WebSocket connections"""
    if not websocket_connections:
        return
    
    try:
        # Send simulation data
        state_json = json.dumps(simulation_data, default=str)
        
        # Send to all connected clients
        disconnected = []
        for websocket in websocket_connections:
            try:
                await websocket.send_text(state_json)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections.remove(ws)
            
    except Exception as e:
        print(f"Error broadcasting state: {e}")

@app.post("/mode")
async def set_mode(request: ModeRequest):
    """Switch between static and RL modes"""
    global current_mode
    
    if request.mode not in ["static", "rl"]:
        return {"error": "Mode must be 'static' or 'rl'"}
    
    current_mode = request.mode
    
    # Update bus fleet mode
    if current_mode == "static":
        simulation_env.bus_fleet.set_mode(BusMode.STATIC)
        simulation_env.baseline_fleet.set_mode(BusMode.STATIC)
    else:
        simulation_env.bus_fleet.set_mode(BusMode.RL)
    
    return {
        "status": "success",
        "mode": current_mode,
        "message": f"Switched to {current_mode} mode"
    }

@app.post("/stress")
async def apply_stress(request: StressRequest):
    """Apply stress scenario"""
    
    try:
        simulation_env.apply_disruption(request.type, request.params)
        
        return {
            "status": "success",
            "type": request.type,
            "params": request.params,
            "message": f"Applied {request.type} disruption"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/reset")
async def reset_simulation(request: ResetRequest):
    """Reset simulation to initial state"""
    
    try:
        # Reset environment
        obs, info = simulation_env.reset(seed=request.seed)
        
        # Reset mode
        if current_mode == "static":
            simulation_env.bus_fleet.set_mode(BusMode.STATIC)
        else:
            simulation_env.bus_fleet.set_mode(BusMode.RL)
        
        return {
            "status": "success",
            "seed": request.seed,
            "message": "Simulation reset successfully"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/status")
async def get_status():
    """Get system status"""
    
    return {
        "mode": current_mode,
        "rl_available": False,  # Simplified for mobile
        "running": is_running,
        "connected_clients": len(websocket_connections),
        "simulation_time": simulation_data.get("time", 0),
        "buses": len(simulation_data.get("buses", [])),
        "stops": len(simulation_data.get("stops", []))
    }

@app.get("/state")
async def get_current_state():
    """Get current system state"""
    
    if simulation_env is None:
        return {"error": "Simulation not initialized"}
    
    return simulation_data

@app.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live system updates"""
    
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        print("WebSocket client disconnected")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global is_running
    is_running = False
    print("Shutting down Mobile Bus Dispatch System...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
