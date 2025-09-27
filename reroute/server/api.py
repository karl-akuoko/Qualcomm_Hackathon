"""
FastAPI server for bus routing simulation control and live data feed.
Provides REST endpoints for control and WebSocket for real-time updates.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.wrappers import BusRoutingEnv
from rl.export_onnx import ONNXInference


# Request/Response models
class ModeRequest(BaseModel):
    mode: str  # "static" or "rl"


class StressRequest(BaseModel):
    type: str  # "closure", "traffic", "surge"
    params: Optional[Dict[str, Any]] = {}


class ResetRequest(BaseModel):
    seed: int = 42


class LiveData(BaseModel):
    timestamp: float
    buses: List[Dict[str, Any]]
    stops: List[Dict[str, Any]]
    kpi: Dict[str, float]
    baseline_kpi: Optional[Dict[str, float]] = None
    active_disruptions: List[Dict[str, Any]] = []


# Global state
class SimulationState:
    def __init__(self):
        self.env: Optional[BusRoutingEnv] = None
        self.onnx_inference: Optional[ONNXInference] = None
        self.mode: str = "static"
        self.is_running: bool = False
        self.connected_clients: List[WebSocket] = []
        self.simulation_task: Optional[asyncio.Task] = None
        self.baseline_kpis: Dict[str, float] = {}
        self.rl_kpis: Dict[str, float] = {}
    
    def reset_environment(self, seed: int = 42):
        """Reset the simulation environment."""
        self.env = BusRoutingEnv(seed=seed)
        self.env.set_baseline_mode(self.mode == "static")
        
        # Load ONNX model if in RL mode
        if self.mode == "rl" and self.onnx_inference is None:
            try:
                onnx_path = "./models/onnx/final_model_optimized.onnx"
                if os.path.exists(onnx_path):
                    self.onnx_inference = ONNXInference(onnx_path)
                    print("ONNX model loaded successfully")
                else:
                    print("ONNX model not found, using fallback RL actions")
                    self.onnx_inference = None
            except Exception as e:
                print(f"Failed to load ONNX model: {e}")
                self.onnx_inference = None
    
    def get_next_action(self) -> np.ndarray:
        """Get next action based on current mode."""
        if self.mode == "static":
            # Baseline: all continue actions
            return np.zeros(self.env.num_buses, dtype=int)
        elif self.mode == "rl" and self.onnx_inference:
            # RL: use ONNX inference
            obs = self.env._get_observation()
            actions, _ = self.onnx_inference.predict(obs.reshape(1, -1))
            return actions[0]  # Remove batch dimension
        elif self.mode == "rl":
            # RL: use simple heuristic actions when ONNX not available
            actions = []
            for bus in self.env.buses:
                # Simple heuristic: go to high demand if queue > 10, otherwise continue
                high_demand_stops = [stop_id for stop_id, stop in self.env.city.stops.items() if stop.queue_len > 10]
                if high_demand_stops and bus.load < bus.capacity * 0.8:
                    actions.append(1)  # GO_TO_HIGH_DEMAND
                else:
                    actions.append(0)  # CONTINUE
            return np.array(actions)
        else:
            # Fallback to random actions
            return np.random.randint(0, 4, size=self.env.num_buses)


# Global simulation state
sim_state = SimulationState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    print("Starting bus routing simulation server...")
    sim_state.reset_environment()
    yield
    # Shutdown
    if sim_state.simulation_task:
        sim_state.simulation_task.cancel()
    print("Server shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Bus Routing Simulation API",
    description="API for controlling RL-driven bus routing simulation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Bus Routing Simulation API",
        "version": "1.0.0",
        "status": "running",
        "mode": sim_state.mode,
        "is_running": sim_state.is_running
    }


@app.get("/status")
async def get_status():
    """Get simulation status."""
    return {
        "mode": sim_state.mode,
        "is_running": sim_state.is_running,
        "connected_clients": len(sim_state.connected_clients),
        "environment_ready": sim_state.env is not None,
        "onnx_loaded": sim_state.onnx_inference is not None
    }


@app.post("/mode")
async def set_mode(request: ModeRequest):
    """Switch between static and RL modes."""
    if request.mode not in ["static", "rl"]:
        raise HTTPException(status_code=400, detail="Mode must be 'static' or 'rl'")
    
    sim_state.mode = request.mode
    
    if sim_state.env:
        sim_state.env.set_baseline_mode(request.mode == "static")
    
    # Load ONNX model if switching to RL mode
    if request.mode == "rl" and sim_state.onnx_inference is None:
        try:
            onnx_path = "./models/onnx/final_model_optimized.onnx"
            sim_state.onnx_inference = ONNXInference(onnx_path)
            print("ONNX model loaded successfully")
        except Exception as e:
            print(f"Failed to load ONNX model: {e}")
            return {"message": f"Mode set to {request.mode}, but ONNX model failed to load: {e}"}
    
    return {"message": f"Mode set to {request.mode}"}


@app.post("/stress")
async def trigger_stress(request: StressRequest):
    """Trigger stress test scenario."""
    if not sim_state.env:
        raise HTTPException(status_code=400, detail="Environment not initialized")
    
    disruption_type = request.type
    params = request.params or {}
    
    try:
        if disruption_type == "closure":
            # Create road closure
            edge = sim_state.env.traffic_manager.get_random_central_edge()
            disruption_id = sim_state.env.trigger_disruption(
                "closure", 
                from_pos=edge[0], 
                to_pos=edge[1],
                duration=params.get("duration", 300)
            )
        elif disruption_type == "traffic":
            # Create traffic slowdown
            edge = sim_state.env.traffic_manager.get_random_central_edge()
            disruption_id = sim_state.env.trigger_disruption(
                "traffic",
                from_pos=edge[0],
                to_pos=edge[1],
                factor=params.get("factor", 3.0),
                duration=params.get("duration", 300)
            )
        elif disruption_type == "surge":
            # Create demand surge
            stops = sim_state.env.traffic_manager.get_high_demand_stops(
                params.get("num_stops", 3)
            )
            disruption_id = sim_state.env.trigger_disruption(
                "surge",
                stop_ids=stops,
                surge_factor=params.get("surge_factor", 3.0),
                duration=params.get("duration", 600)
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown stress type: {disruption_type}")
        
        return {
            "message": f"Stress test '{disruption_type}' triggered",
            "disruption_id": disruption_id,
            "params": params
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger stress test: {e}")


@app.post("/reset")
async def reset_simulation(request: ResetRequest):
    """Reset simulation with new seed."""
    sim_state.reset_environment(request.seed)
    
    # Stop current simulation if running
    if sim_state.simulation_task and not sim_state.simulation_task.done():
        sim_state.simulation_task.cancel()
        sim_state.is_running = False
    
    return {
        "message": "Simulation reset",
        "seed": request.seed,
        "mode": sim_state.mode
    }


@app.get("/kpis")
async def get_kpis():
    """Get current KPIs."""
    if not sim_state.env:
        raise HTTPException(status_code=400, detail="Environment not initialized")
    
    current_kpis = sim_state.env.get_kpis()
    
    return {
        "current": current_kpis,
        "baseline": sim_state.baseline_kpis,
        "rl": sim_state.rl_kpis,
        "mode": sim_state.mode
    }


@app.get("/state")
async def get_state():
    """Get current simulation state."""
    if not sim_state.env:
        raise HTTPException(status_code=400, detail="Environment not initialized")
    
    return sim_state.env.get_state_for_ui()


@app.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live simulation data."""
    await websocket.accept()
    sim_state.connected_clients.append(websocket)
    
    print(f"Client connected. Total clients: {len(sim_state.connected_clients)}")
    
    try:
        # Send initial state
        if sim_state.env:
            initial_state = sim_state.env.get_state_for_ui()
            await websocket.send_text(json.dumps(initial_state))
        
        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(0.1)  # 10 Hz update rate
            
            if sim_state.is_running and sim_state.env:
                # Send current state
                state = sim_state.env.get_state_for_ui()
                await websocket.send_text(json.dumps(state))
            
    except WebSocketDisconnect:
        sim_state.connected_clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(sim_state.connected_clients)}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in sim_state.connected_clients:
            sim_state.connected_clients.remove(websocket)


@app.post("/start")
async def start_simulation():
    """Start the simulation loop."""
    if sim_state.is_running:
        return {"message": "Simulation already running"}
    
    if not sim_state.env:
        sim_state.reset_environment()
    
    sim_state.is_running = True
    sim_state.simulation_task = asyncio.create_task(simulation_loop())
    
    return {"message": "Simulation started"}


@app.post("/stop")
async def stop_simulation():
    """Stop the simulation loop."""
    if not sim_state.is_running:
        return {"message": "Simulation not running"}
    
    sim_state.is_running = False
    
    if sim_state.simulation_task and not sim_state.simulation_task.done():
        sim_state.simulation_task.cancel()
    
    return {"message": "Simulation stopped"}


async def simulation_loop():
    """Main simulation loop."""
    print("Simulation loop started")
    
    while sim_state.is_running and sim_state.env:
        try:
            # Get next action
            action = sim_state.get_next_action()
            
            # Step environment
            obs, reward, terminated, truncated, info = sim_state.env.step(action)
            done = terminated or truncated
            
            # Update KPIs based on mode
            current_kpis = sim_state.env.get_kpis()
            if sim_state.mode == "static":
                sim_state.baseline_kpis = current_kpis
            else:
                sim_state.rl_kpis = current_kpis
            
            # Check if episode is done
            if done:
                print("Episode completed, resetting...")
                sim_state.env.reset()
            
            # Small delay to control simulation speed
            await asyncio.sleep(0.1)  # 10 Hz simulation rate
            
        except Exception as e:
            print(f"Simulation loop error: {e}")
            break
    
    print("Simulation loop ended")


@app.get("/demo/script")
async def get_demo_script():
    """Get the demo script for presentation."""
    demo_script = {
        "title": "RL Bus Routing Demo Script",
        "duration_minutes": 7,
        "steps": [
            {
                "step": 1,
                "title": "Setup",
                "duration": 30,
                "description": "Show baseline static routing with morning peak demand",
                "actions": [
                    "Set mode to 'static'",
                    "Start simulation",
                    "Show rising wait times"
                ]
            },
            {
                "step": 2,
                "title": "Switch to RL",
                "duration": 60,
                "description": "Switch to RL mode and show improvement",
                "actions": [
                    "Set mode to 'rl'",
                    "Highlight KPI improvements",
                    "Show bus re-routing behavior"
                ]
            },
            {
                "step": 3,
                "title": "Road Closure Test",
                "duration": 90,
                "description": "Test resilience with road closure",
                "actions": [
                    "Trigger 'closure' stress test",
                    "Show baseline vs RL response",
                    "Highlight recovery time"
                ]
            },
            {
                "step": 4,
                "title": "Demand Surge Test",
                "duration": 90,
                "description": "Test with demand surge at stadium",
                "actions": [
                    "Trigger 'surge' stress test",
                    "Show RL capacity reallocation",
                    "Highlight overcrowding control"
                ]
            },
            {
                "step": 5,
                "title": "Performance Metrics",
                "duration": 60,
                "description": "Show final performance comparison",
                "actions": [
                    "Display improvement percentages",
                    "Show on-device inference stats",
                    "Highlight Snapdragon X Elite performance"
                ]
            }
        ]
    }
    
    return demo_script


if __name__ == "__main__":
    uvicorn.run(
        "server.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
