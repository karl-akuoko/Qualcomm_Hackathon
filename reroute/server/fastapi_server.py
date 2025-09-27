from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Static files not needed - dashboard is embedded in HTML

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
                            // Grid lines
                            Array.from({ length: gridSize + 1 }, (_, i) => 
                                React.createElement('g', { key: i },
                                    React.createElement('line', {
                                        x1: i * scale, y1: 0, x2: i * scale, y2: gridSize * scale,
                                        stroke: "#e5e7eb", strokeWidth: "1"
                                    }),
                                    React.createElement('line', {
                                        x1: 0, y1: i * scale, x2: gridSize * scale, y2: i * scale,
                                        stroke: "#e5e7eb", strokeWidth: "1"
                                    })
                                )
                            ),
                            // Bus stops
                            stops?.map(stop => 
                                React.createElement('g', { key: stop.id },
                                    React.createElement('circle', {
                                        cx: stop.x * scale, cy: stop.y * scale, r: 4,
                                        fill: stop.queue_len > 5 ? '#ef4444' : stop.queue_len > 2 ? '#f59e0b' : '#10b981',
                                        stroke: "#fff", strokeWidth: "1"
                                    }),
                                    stop.queue_len > 0 && React.createElement('text', {
                                        x: stop.x * scale + 6, y: stop.y * scale + 4,
                                        fontSize: "10", fill: "#374151"
                                    }, stop.queue_len)
                                )
                            ),
                            // Buses
                            buses?.map(bus => 
                                React.createElement('g', { key: bus.id },
                                    React.createElement('rect', {
                                        x: bus.x * scale - 6, y: bus.y * scale - 4,
                                        width: "12", height: "8", rx: "2",
                                        fill: bus.is_moving ? '#3b82f6' : '#6366f1',
                                        stroke: "#fff", strokeWidth: "1"
                                    }),
                                    React.createElement('text', {
                                        x: bus.x * scale, y: bus.y * scale + 2,
                                        fontSize: "8", textAnchor: "middle", fill: "white", fontWeight: "bold"
                                    }, bus.id)
                                )
                            )
                        )
                    )
                );
            };
            
            // KPI Card component
            const KPICard = ({ title, value, baselineValue, unit = '', improvement }) => {
                const improvementPercent = improvement != null ? (improvement * 100) : 0;
                const isPositive = improvement > 0;
                
                return React.createElement('div', { className: "bg-white rounded-lg shadow p-4" },
                    React.createElement('h4', { className: "text-sm font-medium text-gray-600 mb-2" }, title),
                    React.createElement('div', { className: "text-2xl font-bold text-gray-900 mb-1" },
                        typeof value === 'number' ? value.toFixed(2) : value, unit
                    ),
                    baselineValue != null && React.createElement('div', { className: "text-sm text-gray-500 mb-2" },
                        "Baseline: ", baselineValue.toFixed(2), unit
                    ),
                    improvement != null && React.createElement('div', { 
                        className: `text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}` 
                    },
                        isPositive ? '↑' : '↓', " ", Math.abs(improvementPercent).toFixed(1), "%"
                    )
                );
            };
            
            // Main Dashboard Component
            function Dashboard() {
                const [systemState, setSystemState] = useState(null);
                const [kpiHistory, setKpiHistory] = useState([]);
                const [currentMode, setCurrentMode] = useState('static');
                const [status, setStatus] = useState({});
                const [isConnected, setIsConnected] = useState(false);
                const wsRef = useRef(null);
                
                // WebSocket connection
                useEffect(() => {
                    const connectWebSocket = () => {
                        try {
                            wsRef.current = new WebSocket('ws://localhost:8000/live');
                            
                            wsRef.current.onopen = () => {
                                console.log('WebSocket connected');
                                setIsConnected(true);
                            };
                            
                            wsRef.current.onmessage = (event) => {
                                try {
                                    const state = JSON.parse(event.data);
                                    setSystemState(state);
                                    
                                    // Update KPI history
                                    setKpiHistory(prev => {
                                        const newEntry = {
                                            time: state.time,
                                            rl_avg_wait: state.kpi?.avg_wait || 0,
                                            baseline_avg_wait: state.baseline_kpi?.avg_wait || 0,
                                            rl_load_std: state.kpi?.load_std || 0,
                                            baseline_load_std: state.baseline_kpi?.load_std || 0
                                        };
                                        
                                        const updated = [...prev, newEntry].slice(-100);
                                        return updated;
                                    });
                                } catch (error) {
                                    console.error('Error parsing WebSocket message:', error);
                                }
                            };
                            
                            wsRef.current.onclose = () => {
                                console.log('WebSocket disconnected');
                                setIsConnected(false);
                                setTimeout(connectWebSocket, 3000);
                            };
                            
                            wsRef.current.onerror = (error) => {
                                console.error('WebSocket error:', error);
                            };
                        } catch (error) {
                            console.error('Error creating WebSocket:', error);
                            setTimeout(connectWebSocket, 3000);
                        }
                    };
                    
                    connectWebSocket();
                    
                    return () => {
                        if (wsRef.current) {
                            wsRef.current.close();
                        }
                    };
                }, []);
                
                // Fetch system status
                useEffect(() => {
                    const fetchStatus = async () => {
                        try {
                            const response = await fetch('http://localhost:8000/status');
                            const data = await response.json();
                            setStatus(data);
                            setCurrentMode(data.mode);
                        } catch (error) {
                            console.error('Error fetching status:', error);
                        }
                    };
                    
                    fetchStatus();
                    const interval = setInterval(fetchStatus, 5000);
                    return () => clearInterval(interval);
                }, []);
                
                // API calls
                const switchMode = async (mode) => {
                    try {
                        const response = await fetch('http://localhost:8000/mode', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ mode })
                        });
                        
                        if (response.ok) {
                            setCurrentMode(mode);
                        }
                    } catch (error) {
                        console.error('Error switching mode:', error);
                    }
                };
                
                const applyStress = async (type, params = {}) => {
                    try {
                        await fetch('http://localhost:8000/stress', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ type, params })
                        });
                    } catch (error) {
                        console.error('Error applying stress:', error);
                    }
                };
                
                const resetSimulation = async () => {
                    try {
                        await fetch('http://localhost:8000/reset', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ seed: 42 })
                        });
                        setKpiHistory([]);
                    } catch (error) {
                        console.error('Error resetting simulation:', error);
                    }
                };
                
                // Calculate improvements
                const getImprovements = () => {
                    if (!systemState?.kpi || !systemState?.baseline_kpi) return {};
                    
                    const rl = systemState.kpi;
                    const baseline = systemState.baseline_kpi;
                    
                    return {
                        avg_wait: baseline.avg_wait > 0 ? (baseline.avg_wait - rl.avg_wait) / baseline.avg_wait : 0,
                        overcrowd: baseline.load_std > 0 ? (baseline.load_std - rl.load_std) / baseline.load_std : 0
                    };
                };
                
                const improvements = getImprovements();
                
                return React.createElement('div', { className: "min-h-screen bg-gray-100 p-6" },
                    React.createElement('div', { className: "max-w-7xl mx-auto" },
                        // Header
                        React.createElement('div', { className: "flex justify-between items-center mb-6" },
                            React.createElement('h1', { className: "text-3xl font-bold text-gray-900" },
                                "Bus Dispatch RL Demo"
                            ),
                            React.createElement('div', { className: "flex items-center gap-4" },
                                React.createElement('div', { 
                                    className: `flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
                                        isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                    }` 
                                },
                                    React.createElement('div', { 
                                        className: `w-2 h-2 rounded-full ${
                                            isConnected ? 'bg-green-500' : 'bg-red-500'
                                        }` 
                                    }),
                                    isConnected ? 'Connected' : 'Disconnected'
                                ),
                                React.createElement('div', { className: "text-sm text-gray-600" },
                                    "Time: ", systemState?.time?.toFixed(1) || 0, "m"
                                )
                            )
                        ),
                        
                        // Mode Controls
                        React.createElement('div', { className: "bg-white rounded-lg shadow p-4 mb-6" },
                            React.createElement('div', { className: "flex items-center justify-between" },
                                React.createElement('div', { className: "flex items-center gap-4" },
                                    React.createElement('span', { className: "text-lg font-semibold" }, "Operation Mode:"),
                                    React.createElement('div', { className: "flex gap-2" },
                                        React.createElement('button', {
                                            onClick: () => switchMode('static'),
                                            className: `px-4 py-2 rounded-lg font-medium ${
                                                currentMode === 'static' 
                                                    ? 'bg-blue-500 text-white' 
                                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                            }`
                                        }, "Static Schedule"),
                                        React.createElement('button', {
                                            onClick: () => switchMode('rl'),
                                            disabled: !status.rl_available,
                                            className: `px-4 py-2 rounded-lg font-medium ${
                                                currentMode === 'rl' 
                                                    ? 'bg-green-500 text-white' 
                                                    : status.rl_available 
                                                        ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                            }`
                                        }, "RL Policy ", !status.rl_available && '(Unavailable)')
                                    )
                                ),
                                
                                // Stress Test Controls
                                React.createElement('div', { className: "flex items-center gap-2" },
                                    React.createElement('span', { className: "text-sm font-medium text-gray-600" }, "Disruptions:"),
                                    React.createElement('button', {
                                        onClick: () => applyStress('closure', { stop_id: 210 }),
                                        className: "px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
                                    }, "Road Closure"),
                                    React.createElement('button', {
                                        onClick: () => applyStress('traffic', { factor: 2.0 }),
                                        className: "px-3 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600 text-sm"
                                    }, "Traffic Jam"),
                                    React.createElement('button', {
                                        onClick: () => applyStress('surge', { multiplier: 3.0 }),
                                        className: "px-3 py-1 bg-orange-500 text-white rounded hover:bg-orange-600 text-sm"
                                    }, "Demand Surge"),
                                    React.createElement('button', {
                                        onClick: resetSimulation,
                                        className: "px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
                                    }, "Reset")
                                )
                            )
                        ),
                        
                        // Side-by-side Maps
                        React.createElement('div', { className: "grid grid-cols-2 gap-6 mb-6" },
                            React.createElement(BusMap, {
                                title: "Static Schedule (Baseline)",
                                buses: systemState?.buses?.filter(b => b.mode === 'static') || [],
                                stops: systemState?.stops || []
                            }),
                            React.createElement(BusMap, {
                                title: "RL Policy (Adaptive)",
                                buses: systemState?.buses?.filter(b => b.mode === 'rl') || [],
                                stops: systemState?.stops || []
                            })
                        ),
                        
                        // KPI Cards
                        React.createElement('div', { className: "grid grid-cols-4 gap-4 mb-6" },
                            React.createElement(KPICard, {
                                title: "Average Wait Time",
                                value: systemState?.kpi?.avg_wait,
                                baselineValue: systemState?.baseline_kpi?.avg_wait,
                                unit: " min",
                                improvement: improvements.avg_wait
                            }),
                            React.createElement(KPICard, {
                                title: "90th Percentile Wait",
                                value: systemState?.kpi?.p90_wait,
                                baselineValue: systemState?.baseline_kpi?.p90_wait,
                                unit: " min"
                            }),
                            React.createElement(KPICard, {
                                title: "Load Std Dev",
                                value: systemState?.kpi?.load_std,
                                baselineValue: systemState?.baseline_kpi?.load_std,
                                improvement: improvements.overcrowd
                            }),
                            React.createElement(KPICard, {
                                title: "System Status",
                                value: currentMode.toUpperCase(),
                                baselineValue: null,
                                unit: ""
                            })
                        ),
                        
                        // Performance Charts
                        React.createElement('div', { className: "grid grid-cols-1 gap-6" },
                            // Wait Time Chart
                            React.createElement('div', { className: "bg-white rounded-lg shadow p-4" },
                                React.createElement('h3', { className: "text-lg font-semibold mb-4" }, "Wait Time Comparison"),
                                React.createElement(ResponsiveContainer, { width: "100%", height: 300 },
                                    React.createElement(LineChart, { data: kpiHistory },
                                        React.createElement(CartesianGrid, { strokeDasharray: "3 3" }),
                                        React.createElement(XAxis, { 
                                            dataKey: "time", 
                                            label: { value: 'Time (minutes)', position: 'insideBottom', offset: -5 }
                                        }),
                                        React.createElement(YAxis, { 
                                            label: { value: 'Wait Time (minutes)', angle: -90, position: 'insideLeft' }
                                        }),
                                        React.createElement(Tooltip),
                                        React.createElement(Line, { 
                                            type: "monotone", 
                                            dataKey: "baseline_avg_wait", 
                                            stroke: "#ef4444", 
                                            strokeWidth: 2,
                                            name: "Baseline (Static)"
                                        }),
                                        React.createElement(Line, { 
                                            type: "monotone", 
                                            dataKey: "rl_avg_wait", 
                                            stroke: "#10b981", 
                                            strokeWidth: 2,
                                            name: "RL Policy"
                                        })
                                    )
                                )
                            ),
                            
                            // Load Distribution Chart
                            React.createElement('div', { className: "bg-white rounded-lg shadow p-4" },
                                React.createElement('h3', { className: "text-lg font-semibold mb-4" }, "Load Distribution (Overcrowding)"),
                                React.createElement(ResponsiveContainer, { width: "100%", height: 200 },
                                    React.createElement(LineChart, { data: kpiHistory },
                                        React.createElement(CartesianGrid, { strokeDasharray: "3 3" }),
                                        React.createElement(XAxis, { 
                                            dataKey: "time", 
                                            label: { value: 'Time (minutes)', position: 'insideBottom', offset: -5 }
                                        }),
                                        React.createElement(YAxis, { 
                                            label: { value: 'Load Std Dev', angle: -90, position: 'insideLeft' }
                                        }),
                                        React.createElement(Tooltip),
                                        React.createElement(Line, { 
                                            type: "monotone", 
                                            dataKey: "baseline_load_std", 
                                            stroke: "#f59e0b", 
                                            strokeWidth: 2,
                                            name: "Baseline"
                                        }),
                                        React.createElement(Line, { 
                                            type: "monotone", 
                                            dataKey: "rl_load_std", 
                                            stroke: "#3b82f6", 
                                            strokeWidth: 2,
                                            name: "RL Policy"
                                        })
                                    )
                                )
                            )
                        ),
                        
                        // Footer
                        React.createElement('div', { className: "mt-6 text-center text-sm text-gray-500" },
                            React.createElement('p', null, "Bus Dispatch RL Demo - Real-time adaptive routing with reinforcement learning"),
                            React.createElement('p', null, "Green improvements indicate RL is outperforming the baseline static schedule")
                        )
                    )
                );
            }
            
            ReactDOM.render(React.createElement(Dashboard), document.getElementById('root'));
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

@app.get("/demo")
async def get_demo_scenario():
    """Get pre-configured demo scenario"""
    
    demo_script = {
        "duration_minutes": 7,
        "steps": [
            {
                "time": 0,
                "action": "start",
                "description": "Start in Static mode during morning peak",
                "api_calls": [
                    {"endpoint": "/mode", "data": {"mode": "static"}},
                    {"endpoint": "/reset", "data": {"seed": 42}}
                ]
            },
            {
                "time": 90,
                "action": "switch_to_rl",
                "description": "Switch to RL mode - watch KPIs improve",
                "api_calls": [
                    {"endpoint": "/mode", "data": {"mode": "rl"}}
                ]
            },
            {
                "time": 180,
                "action": "road_closure",
                "description": "Trigger road closure on central avenue",
                "api_calls": [
                    {"endpoint": "/stress", "data": {"type": "closure", "params": {"stop_id": 210}}}
                ]
            },
            {
                "time": 300,
                "action": "demand_surge",
                "description": "Create surge near stadium area",
                "api_calls": [
                    {"endpoint": "/stress", "data": {"type": "surge", "params": {"stop_id": 156, "multiplier": 3.0}}}
                ]
            },
            {
                "time": 420,
                "action": "final_comparison",
                "description": "Final comparison - RL vs Static performance",
                "api_calls": []
            }
        ]
    }
    
    return demo_script

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global is_running
    is_running = False
    print("Shutting down Bus Dispatch System...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
