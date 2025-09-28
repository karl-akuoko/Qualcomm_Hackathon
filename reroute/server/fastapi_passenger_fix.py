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

# Try to load trained model
try:
    from stable_baselines3 import PPO
    trained_model = None
    if os.path.exists("best_bus_model.zip"):
        trained_model = PPO.load("best_bus_model.zip")
        print("✅ Loaded trained RL model")
    else:
        print("⚠ No trained model found, using static mode")
except ImportError:
    print("⚠ Stable Baselines3 not available, using static mode")
    trained_model = None

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

app = FastAPI(title="Bus Dispatch RL - Passenger Fix", version="1.0.0")

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
    """Serve the dashboard with passenger boarding fixes"""
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bus Dispatch RL - Passenger Fix</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #1f2937;
                min-height: 100vh;
            }
            .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
            .header { 
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                color: #1f2937; 
                padding: 20px; 
                border-radius: 16px; 
                margin-bottom: 20px; 
                text-align: center;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .status { 
                padding: 8px 16px; 
                border-radius: 25px; 
                margin: 8px 0; 
                font-size: 14px;
                display: inline-block;
                font-weight: 600;
            }
            .status.connected { background: #10b981; color: white; }
            .status.disconnected { background: #ef4444; color: white; }
            .controls { 
                display: grid; 
                grid-template-columns: repeat(3, 1fr); 
                gap: 12px; 
                margin: 20px 0; 
            }
            .btn { 
                padding: 14px 20px; 
                border: none; 
                border-radius: 12px; 
                cursor: pointer; 
                font-weight: 600; 
                font-size: 14px;
                text-align: center;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            .btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.2); }
            .btn:active { transform: translateY(0); }
            .btn-primary { background: #3b82f6; color: white; }
            .btn-success { background: #10b981; color: white; }
            .btn-danger { background: #ef4444; color: white; }
            .btn-warning { background: #f59e0b; color: white; }
            .btn-secondary { background: #6b7280; color: white; }
            .btn-info { background: #06b6d4; color: white; }
            .kpi-grid { 
                display: grid; 
                grid-template-columns: repeat(4, 1fr); 
                gap: 15px; 
                margin: 20px 0; 
            }
            .kpi-card { 
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 20px; 
                border-radius: 16px; 
                text-align: center; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .kpi-value { font-size: 28px; font-weight: bold; color: #1f2937; margin-bottom: 5px; }
            .kpi-label { font-size: 12px; color: #6b7280; font-weight: 500; }
            .map-container { 
                width: 100%; 
                height: 500px; 
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 16px; 
                background: rgba(255, 255, 255, 0.9);
                backdrop-filter: blur(10px);
                position: relative; 
                overflow: hidden;
                margin: 20px 0;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
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
                opacity: 0.6;
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
                width: 28px; 
                height: 28px; 
                background: #3b82f6; 
                border-radius: 50%; 
                border: 3px solid white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                transition: all 0.5s ease;
                z-index: 20;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
                color: white;
                cursor: pointer;
            }
            .bus.rl { background: #10b981; }
            .bus.static { background: #6b7280; }
            .bus.loaded { 
                background: #f59e0b !important; 
                animation: pulse 1.5s infinite;
                box-shadow: 0 0 20px rgba(245, 158, 11, 0.5);
            }
            .bus:hover { transform: scale(1.2); z-index: 25; }
            .stop { 
                position: absolute; 
                width: 24px; 
                height: 24px; 
                background: #ef4444; 
                border-radius: 50%; 
                border: 3px solid white;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10;
                cursor: pointer;
            }
            .stop::after {
                content: '';
                position: absolute;
                top: -4px;
                left: -4px;
                right: -4px;
                bottom: -4px;
                border: 3px solid #ef4444;
                border-radius: 50%;
                opacity: 0.3;
                animation: pulse 2s infinite;
            }
            .stop.waiting {
                background: #f59e0b;
                animation: pulse 1s infinite;
                box-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
            }
            .stop:hover { transform: scale(1.3); z-index: 15; }
            @keyframes pulse {
                0% { transform: scale(1); opacity: 0.3; }
                50% { transform: scale(1.1); opacity: 0.1; }
                100% { transform: scale(1); opacity: 0.3; }
            }
            .info-panel { 
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 20px; 
                border-radius: 16px; 
                margin: 20px 0; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .chart { 
                height: 200px; 
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 16px; 
                padding: 20px; 
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .legend {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin: 15px 0;
                flex-wrap: wrap;
            }
            .legend-item {
                display: flex;
                align-items: center;
                gap: 8px;
                background: rgba(255, 255, 255, 0.9);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
            }
            .legend-color {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 2px solid white;
            }
            .mobile-optimized { font-size: 14px; }
            @media (max-width: 768px) {
                .container { padding: 10px; }
                .controls { grid-template-columns: 1fr; }
                .kpi-grid { grid-template-columns: repeat(2, 1fr); }
                .btn { padding: 12px; font-size: 14px; }
                .map-container { height: 400px; }
            }
        </style>
    </head>
    <body>
        <div class="container mobile-optimized">
            <div class="header">
                <h1>🚌 Bus Dispatch RL - Passenger Fix</h1>
                <div id="status" class="status disconnected">Disconnected</div>
                <div>Time: <span id="time">0.0</span>m | Mode: <span id="mode">static</span> | RL Model: <span id="rl-status">Not Available</span></div>
            </div>
            
            <div class="info-panel">
                <h3>System Status</h3>
                <div id="system-info">Loading...</div>
            </div>
            
            <div class="controls">
                <button class="btn btn-primary" onclick="switchMode('static')">Static Schedule</button>
                <button class="btn btn-success" onclick="switchMode('rl')">RL Policy</button>
                <button class="btn btn-info" onclick="trainModel()">Train Model</button>
                <button class="btn btn-danger" onclick="applyStress('closure')">Road Closure</button>
                <button class="btn btn-warning" onclick="applyStress('traffic')">Traffic Jam</button>
                <button class="btn btn-warning" onclick="applyStress('surge')">Demand Surge</button>
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
            
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #3b82f6;"></div>
                    <span>Static Buses</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #10b981;"></div>
                    <span>RL Buses</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f59e0b;"></div>
                    <span>Loaded Buses</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ef4444;"></div>
                    <span>Bus Stops</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f59e0b; animation: pulse 1s infinite;"></div>
                    <span>Stops with Passengers</span>
                </div>
            </div>
            
            <div class="card">
                <h3>Manhattan Grid Simulation - Passenger Fix</h3>
                <div class="map-container" id="map">
                    <div class="grid-lines" id="grid-lines"></div>
                </div>
            </div>
            
            <div class="info-panel">
                <h3>Performance Analytics</h3>
                <div class="chart" id="chart">
                    <div style="text-align: center; padding-top: 80px; color: #6b7280;">
                        Performance metrics and charts will appear here...
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
                    line.style.top = (i * (500 / gridSize)) + 'px';
                    gridLines.appendChild(line);
                }
                
                // Create vertical lines
                for (let i = 0; i <= gridSize; i++) {
                    const line = document.createElement('div');
                    line.className = 'grid-line vertical';
                    line.style.left = (i * (500 / gridSize)) + 'px';
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
                        if (stop.queue_len > 0) {
                            stopElement.className += ' waiting';
                        }
                        stopElement.style.left = (stop.x * (500 / gridSize) - 12) + 'px';
                        stopElement.style.top = (stop.y * (500 / gridSize) - 12) + 'px';
                        stopElement.title = `Stop ${stop.id}: ${stop.queue_len} passengers waiting`;
                        container.appendChild(stopElement);
                    });
                }
                
                // Add buses
                if (systemState.buses) {
                    systemState.buses.forEach(bus => {
                        const busElement = document.createElement('div');
                        busElement.className = `bus ${bus.mode}`;
                        if (bus.load > 0) {
                            busElement.className += ' loaded';
                        }
                        busElement.style.left = (bus.x * (500 / gridSize) - 14) + 'px';
                        busElement.style.top = (bus.y * (500 / gridSize) - 14) + 'px';
                        busElement.textContent = bus.load;
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
            
            async function trainModel() {
                try {
                    const response = await fetch('/train', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });
                    if (response.ok) {
                        alert('Training started! Check server logs for progress.');
                    } else {
                        alert('Training failed. Check server logs.');
                    }
                } catch (error) {
                    console.error('Error starting training:', error);
                    alert('Error starting training: ' + error.message);
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
                    document.getElementById('rl-status').textContent = data.rl_available ? 'Available' : 'Not Available';
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
    """Initialize simulation environment with passenger boarding fixes"""
    global simulation_env
    
    print("Initializing Bus Dispatch System with Passenger Fixes...")
    
    # Initialize environment
    simulation_env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=float('inf'),
        seed=42
    )
    
    # Reset environment
    obs, info = simulation_env.reset()
    
    # Start simulation loop
    asyncio.create_task(simulation_loop())
    
    print("Bus Dispatch System with Passenger Fixes initialized successfully!")

async def simulation_loop():
    """Simulation loop with passenger boarding fixes"""
    global simulation_env, is_running, simulation_data
    
    is_running = True
    
    while is_running:
        try:
            # Get current observation
            obs = simulation_env._get_observation()
            
            # Generate actions based on mode and model availability
            if current_mode == "rl" and trained_model is not None:
                # Use trained RL model
                actions, _ = trained_model.predict(obs, deterministic=True)
                if isinstance(actions, np.ndarray):
                    actions = actions.tolist()
            else:
                # Static mode or no trained model - use more intelligent actions
                actions = []
                for bus_id in range(simulation_env.num_buses):
                    # Get bus state
                    bus = simulation_env.bus_fleet.buses[bus_id]
                    
                    # Simple heuristic: if bus is empty, go to high-demand stop
                    if bus.load == 0:
                        # Find stop with most passengers
                        max_queue = 0
                        target_stop = None
                        for stop in simulation_env.city_grid.stops:
                            if stop.queue_len > max_queue:
                                max_queue = stop.queue_len
                                target_stop = stop.id
                        
                        if target_stop is not None and max_queue > 0:
                            actions.append(1)  # HIGH_DEMAND
                        else:
                            actions.append(0)  # CONTINUE
                    else:
                        # If bus has passengers, continue to next stop
                        actions.append(0)  # CONTINUE
            
            # Step environment
            obs, reward, done, truncated, info = simulation_env.step(np.array(actions))
            
            # Reset if episode ended
            if done or truncated:
                obs, info = simulation_env.reset()
            
            # Update simulation data with better passenger tracking
            simulation_data = get_enhanced_system_state()
            
            # Broadcast state to WebSocket clients
            await broadcast_state()
            
            # Control simulation speed (1 Hz for better observation)
            await asyncio.sleep(1.0)
            
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            await asyncio.sleep(1.0)

def get_enhanced_system_state():
    """Get enhanced system state with better passenger tracking"""
    
    if simulation_env is None:
        return {"time": 0.0, "buses": [], "stops": [], "kpi": {"avg_wait": 0.0, "load_std": 0.0}}
    
    # Get bus states
    buses = []
    for bus_id, bus in enumerate(simulation_env.bus_fleet.buses):
        buses.append({
            "id": bus_id,
            "x": bus.x,
            "y": bus.y,
            "load": bus.load,
            "capacity": bus.capacity,
            "next_stop": bus.next_stop,
            "mode": bus.mode.value if hasattr(bus.mode, 'value') else str(bus.mode)
        })
    
    # Get stop states
    stops = []
    total_waiting = 0
    for stop in simulation_env.city_grid.stops:
        stops.append({
            "id": stop.id,
            "x": stop.x,
            "y": stop.y,
            "queue_len": stop.queue_len,
            "total_wait": stop.total_wait_time
        })
        total_waiting += stop.queue_len
    
    # Calculate KPIs
    total_bus_load = sum(bus["load"] for bus in buses)
    avg_wait = simulation_env.current_time / max(total_waiting, 1) if total_waiting > 0 else 0.0
    
    # Calculate load standard deviation
    if buses:
        loads = [bus["load"] for bus in buses]
        load_std = np.std(loads) if len(loads) > 1 else 0.0
    else:
        load_std = 0.0
    
    return {
        "time": simulation_env.current_time,
        "buses": buses,
        "stops": stops,
        "kpi": {
            "avg_wait": avg_wait,
            "load_std": load_std,
            "total_waiting": total_waiting,
            "total_bus_load": total_bus_load
        },
        "baseline_kpi": {
            "avg_wait": avg_wait,  # Same for now
            "load_std": load_std
        }
    }

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
    
    if request.mode == "rl" and trained_model is None:
        return {"error": "RL mode not available - no trained model"}
    
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

@app.post("/train")
async def start_training():
    """Start training a new RL model"""
    
    try:
        # Run training in background
        asyncio.create_task(run_training())
        
        return {
            "status": "success",
            "message": "Training started - check server logs for progress"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

async def run_training():
    """Run training in background"""
    
    print("🤖 Starting advanced training...")
    
    try:
        import subprocess
        import sys
        
        # Run advanced training script
        result = subprocess.run([
            sys.executable, '../train_advanced.py'
        ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
        
        if result.returncode == 0:
            print("✅ Training completed successfully")
            # Reload model
            await reload_trained_model()
        else:
            print(f"❌ Training failed: {result.stderr}")
    
    except Exception as e:
        print(f"❌ Training error: {e}")

async def reload_trained_model():
    """Reload trained model after training"""
    global trained_model
    
    try:
        if os.path.exists("best_bus_model.zip"):
            from stable_baselines3 import PPO
            trained_model = PPO.load("best_bus_model.zip")
            print("✅ Trained model reloaded successfully")
        else:
            print("⚠ No trained model found")
    except Exception as e:
        print(f"❌ Failed to reload model: {e}")

@app.get("/status")
async def get_status():
    """Get system status"""
    
    return {
        "mode": current_mode,
        "rl_available": trained_model is not None,
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
    print("Shutting down Bus Dispatch System with Passenger Fixes...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
