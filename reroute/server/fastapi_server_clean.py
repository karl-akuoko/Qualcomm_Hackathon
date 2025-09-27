from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
import json
import numpy as np
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
sys.path.append(os.path.join(parent_dir, 'env'))
sys.path.append(os.path.join(parent_dir, 'rl'))

from env.wrappers import BusDispatchEnv
from env.bus import BusMode
try:
    from rl.export_onnx import ONNXPolicyInference
except ImportError:
    ONNXPolicyInference = None
from typing import Dict, List, Optional, Any
import time

# Pydantic models for API
class ModeRequest(BaseModel):
    mode: str  # "static" or "rl"

class StressRequest(BaseModel):
    type: str  # "closure", "traffic", "surge"
    params: Dict[str, Any] = {}

class ResetRequest(BaseModel):
    seed: int = 42

class SystemState(BaseModel):
    t: float
    buses: List[Dict[str, Any]]
    stops: List[Dict[str, Any]]
    kpi: Dict[str, float]
    baseline_kpi: Dict[str, float]

# Global simulation state
simulation_env = None
onnx_policy = None
current_mode = "static"
is_running = False
websocket_connections = []

app = FastAPI(title="Bus Dispatch RL API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard"""
    dashboard_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bus Dispatch RL Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
            .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .controls { display: flex; gap: 10px; margin: 20px 0; }
            .btn { padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
            .btn-primary { background: #3b82f6; color: white; }
            .btn-success { background: #10b981; color: white; }
            .btn-danger { background: #ef4444; color: white; }
            .btn-warning { background: #f59e0b; color: white; }
            .btn-secondary { background: #6b7280; color: white; }
            .status { padding: 10px; border-radius: 4px; margin: 10px 0; }
            .status.connected { background: #d1fae5; color: #065f46; }
            .status.disconnected { background: #fee2e2; color: #991b1b; }
            .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
            .kpi-card { background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .kpi-value { font-size: 24px; font-weight: bold; color: #1f2937; }
            .kpi-label { font-size: 14px; color: #6b7280; margin-top: 5px; }
            .map-container { width: 100%; height: 300px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; position: relative; }
            .bus { position: absolute; width: 12px; height: 8px; background: #3b82f6; border-radius: 2px; }
            .stop { position: absolute; width: 8px; height: 8px; background: #10b981; border-radius: 50%; }
            .chart { height: 200px; background: white; border-radius: 8px; padding: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚌 Bus Dispatch RL Dashboard</h1>
                <div id="status" class="status disconnected">Disconnected</div>
                <div>Time: <span id="time">0.0</span>m | Mode: <span id="mode">static</span></div>
            </div>
            
            <div class="controls">
                <button class="btn btn-primary" onclick="switchMode('static')">Static Schedule</button>
                <button class="btn btn-success" onclick="switchMode('rl')">RL Policy</button>
                <button class="btn btn-danger" onclick="applyStress('closure')">Road Closure</button>
                <button class="btn btn-warning" onclick="applyStress('traffic')">Traffic Jam</button>
                <button class="btn btn-warning" onclick="applyStress('surge')">Demand Surge</button>
                <button class="btn btn-secondary" onclick="resetSim()">Reset</button>
            </div>
            
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-value" id="rl-wait">0.0</div>
                    <div class="kpi-label">RL Avg Wait (min)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value" id="baseline-wait">0.0</div>
                    <div class="kpi-label">Baseline Avg Wait (min)</div>
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
            
            <div class="grid">
                <div class="card">
                    <h3>Static Schedule (Baseline)</h3>
                    <div class="map-container" id="static-map">
                        <div style="text-align: center; padding-top: 120px; color: #6b7280;">
                            Loading buses...
                        </div>
                    </div>
                </div>
                <div class="card">
                    <h3>RL Policy (Adaptive)</h3>
                    <div class="map-container" id="rl-map">
                        <div style="text-align: center; padding-top: 120px; color: #6b7280;">
                            Loading buses...
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>Performance Metrics</h3>
                <div class="chart" id="chart">
                    <div style="text-align: center; padding-top: 80px; color: #6b7280;">
                        Loading performance data...
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let systemState = null;
            
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
                
                // Update maps
                updateMap('static-map', systemState.buses ? systemState.buses.filter(b => b.mode === 'static') : []);
                updateMap('rl-map', systemState.buses ? systemState.buses.filter(b => b.mode === 'rl') : []);
            }
            
            function updateMap(containerId, buses) {
                const container = document.getElementById(containerId);
                container.innerHTML = '';
                
                if (!buses || buses.length === 0) {
                    container.innerHTML = '<div style="text-align: center; padding-top: 120px; color: #6b7280;">No buses</div>';
                    return;
                }
                
                buses.forEach(bus => {
                    const busElement = document.createElement('div');
                    busElement.className = 'bus';
                    busElement.style.left = (bus.x * 15 + 10) + 'px';
                    busElement.style.top = (bus.y * 15 + 10) + 'px';
                    busElement.title = `Bus ${bus.id}: ${bus.load}/${bus.capacity} passengers`;
                    container.appendChild(busElement);
                });
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
            connectWebSocket();
            
            // Fetch initial status
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('mode').textContent = data.mode || 'static';
                })
                .catch(error => console.error('Error fetching status:', error));
        </script>
    </body>
    </html>
    """
    return dashboard_html

@app.on_event("startup")
async def startup_event():
    """Initialize simulation environment and policy"""
    global simulation_env, onnx_policy
    
    print("Initializing Bus Dispatch System...")
    
    # Initialize environment
    simulation_env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=0.5,  # 30 seconds
        max_episode_time=float('inf'),  # Continuous operation
        seed=42
    )
    
    # Try to load ONNX policy
    onnx_path = "../rl/ppo_bus_policy.onnx"
    if os.path.exists(onnx_path):
        try:
            onnx_policy = ONNXPolicyInference(onnx_path)
            print("✓ ONNX policy loaded successfully")
        except Exception as e:
            print(f"✗ Failed to load ONNX policy: {e}")
            print("RL mode will not be available")
    else:
        print(f"ONNX policy not found at {onnx_path}")
        print("Run export_onnx.py first to enable RL mode")
    
    # Reset environment
    simulation_env.reset()
    
    # Start simulation loop
    asyncio.create_task(simulation_loop())
    
    print("System initialized successfully!")

async def simulation_loop():
    """Main simulation loop"""
    global simulation_env, is_running
    
    is_running = True
    
    while is_running:
        try:
            # Get current observation
            obs = simulation_env._get_observation()
            
            # Generate action based on current mode
            if current_mode == "rl" and onnx_policy is not None:
                # RL mode
                actions = onnx_policy.predict(obs, deterministic=True)
                if isinstance(actions, np.ndarray):
                    actions = actions.tolist()
            else:
                # Static mode - no actions needed (buses follow fixed routes)
                actions = [0] * simulation_env.num_buses  # CONTINUE action
            
            # Step environment
            obs, reward, done, info = simulation_env.step(np.array(actions))
            
            # Reset if episode ended (shouldn't happen in continuous mode)
            if done:
                simulation_env.reset()
            
            # Broadcast state to WebSocket clients
            await broadcast_state()
            
            # Control simulation speed (10 Hz update rate)
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Error in simulation loop: {e}")
            await asyncio.sleep(1.0)

async def broadcast_state():
    """Broadcast current system state to all WebSocket connections"""
    if not websocket_connections:
        return
    
    try:
        # Get current system state
        state = simulation_env.get_system_state()
        state_json = json.dumps(state, default=str)
        
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
    
    if request.mode == "rl" and onnx_policy is None:
        return {"error": "RL mode not available - ONNX policy not loaded"}
    
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
    """Apply stress scenario (closure, traffic, surge)"""
    
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
        simulation_env.reset(seed=request.seed)
        
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
        "rl_available": onnx_policy is not None,
        "running": is_running,
        "connected_clients": len(websocket_connections),
        "simulation_time": simulation_env.current_time if simulation_env else 0,
        "buses": len(simulation_env.bus_fleet.buses) if simulation_env else 0,
        "stops": len(simulation_env.city_grid.stops) if simulation_env else 0
    }

@app.get("/state")
async def get_current_state():
    """Get current system state (snapshot)"""
    
    if simulation_env is None:
        return {"error": "Simulation not initialized"}
    
    return simulation_env.get_system_state()

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

@app.get("/metrics")
async def get_metrics():
    """Get detailed performance metrics"""
    
    if simulation_env is None:
        return {"error": "Simulation not initialized"}
    
    # Get comprehensive metrics
    info = simulation_env._get_info()
    
    return {
        "time": info["time"],
        "rl_performance": info["rl_stats"],
        "baseline_performance": info["baseline_stats"],
        "improvements": info["improvements"],
        "system_status": {
            "mode": current_mode,
            "rl_available": onnx_policy is not None,
            "connected_clients": len(websocket_connections)
        }
    }

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global is_running
    is_running = False
    print("Shutting down Bus Dispatch System...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
