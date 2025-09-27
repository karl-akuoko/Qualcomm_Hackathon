import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/live';

// Bus visualization component
const BusMap = ({ title, buses, stops, gridSize = 20 }) => {
  const scale = 300 / gridSize;
  
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-lg font-semibold mb-3 text-center">{title}</h3>
      <div className="relative bg-gray-50 border rounded" 
           style={{ width: 320, height: 320, margin: '0 auto' }}>
        <svg width="320" height="320" viewBox="0 0 320 320">
          {/* Grid lines */}
          {Array.from({ length: gridSize + 1 }, (_, i) => (
            <g key={i}>
              <line
                x1={i * scale}
                y1={0}
                x2={i * scale}
                y2={gridSize * scale}
                stroke="#e5e7eb"
                strokeWidth="1"
              />
              <line
                x1={0}
                y1={i * scale}
                x2={gridSize * scale}
                y2={i * scale}
                stroke="#e5e7eb"
                strokeWidth="1"
              />
            </g>
          ))}
          
          {/* Major avenues (every 4th line) */}
          {Array.from({ length: Math.floor(gridSize / 4) + 1 }, (_, i) => (
            <line
              key={`avenue-${i}`}
              x1={i * 4 * scale}
              y1={0}
              x2={i * 4 * scale}
              y2={gridSize * scale}
              stroke="#9ca3af"
              strokeWidth="2"
            />
          ))}
          
          {/* Bus stops */}
          {stops?.map(stop => (
            <g key={stop.id}>
              <circle
                cx={stop.x * scale}
                cy={stop.y * scale}
                r={4}
                fill={stop.queue_len > 5 ? '#ef4444' : stop.queue_len > 2 ? '#f59e0b' : '#10b981'}
                stroke="#fff"
                strokeWidth="1"
              />
              {stop.queue_len > 0 && (
                <text
                  x={stop.x * scale + 6}
                  y={stop.y * scale + 4}
                  fontSize="10"
                  fill="#374151"
                >
                  {stop.queue_len}
                </text>
              )}
            </g>
          ))}
          
          {/* Buses */}
          {buses?.map(bus => (
            <g key={bus.id}>
              <rect
                x={bus.x * scale - 6}
                y={bus.y * scale - 4}
                width="12"
                height="8"
                rx="2"
                fill={bus.is_moving ? '#3b82f6' : '#6366f1'}
                stroke="#fff"
                strokeWidth="1"
              />
              <text
                x={bus.x * scale}
                y={bus.y * scale + 2}
                fontSize="8"
                textAnchor="middle"
                fill="white"
                fontWeight="bold"
              >
                {bus.id}
              </text>
              {/* Load indicator */}
              <rect
                x={bus.x * scale - 6}
                y={bus.y * scale + 5}
                width={12 * (bus.load / bus.capacity)}
                height="2"
                fill={bus.load / bus.capacity > 0.8 ? '#ef4444' : '#10b981'}
              />
            </g>
          ))}
        </svg>
        
        {/* Legend */}
        <div className="absolute bottom-2 left-2 bg-white p-2 rounded shadow text-xs">
          <div className="flex items-center gap-1 mb-1">
            <div className="w-3 h-2 bg-blue-500 rounded"></div>
            <span>Moving Bus</span>
          </div>
          <div className="flex items-center gap-1 mb-1">
            <div className="w-3 h-2 bg-indigo-500 rounded"></div>
            <span>Stopped Bus</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span>Stops (Low/Med/High)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// KPI Card component
const KPICard = ({ title, value, baselineValue, unit = '', improvement }) => {
  const improvementPercent = improvement != null ? (improvement * 100) : 0;
  const isPositive = improvement > 0;
  
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h4 className="text-sm font-medium text-gray-600 mb-2">{title}</h4>
      <div className="text-2xl font-bold text-gray-900 mb-1">
        {typeof value === 'number' ? value.toFixed(2) : value}{unit}
      </div>
      {baselineValue != null && (
        <div className="text-sm text-gray-500 mb-2">
          Baseline: {baselineValue.toFixed(2)}{unit}
        </div>
      )}
      {improvement != null && (
        <div className={`text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
          {isPositive ? '↑' : '↓'} {Math.abs(improvementPercent).toFixed(1)}%
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component
export default function Dashboard() {
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
        wsRef.current = new WebSocket(WS_URL);
        
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
              
              const updated = [...prev, newEntry].slice(-100); // Keep last 100 points
              return updated;
            });
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };
        
        wsRef.current.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          // Reconnect after 3 seconds
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
        const response = await fetch(`${API_BASE}/status`);
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
      const response = await fetch(`${API_BASE}/mode`, {
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
      await fetch(`${API_BASE}/stress`, {
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
      await fetch(`${API_BASE}/reset`, {
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
  
  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Bus Dispatch RL Demo
          </h1>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
              isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            <div className="text-sm text-gray-600">
              Time: {systemState?.time?.toFixed(1) || 0}m
            </div>
          </div>
        </div>
        
        {/* Mode Controls */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-lg font-semibold">Operation Mode:</span>
              <div className="flex gap-2">
                <button
                  onClick={() => switchMode('static')}
                  className={`px-4 py-2 rounded-lg font-medium ${
                    currentMode === 'static' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                  }`}
                >
                  Static Schedule
                </button>
                <button
                  onClick={() => switchMode('rl')}
                  disabled={!status.rl_available}
                  className={`px-4 py-2 rounded-lg font-medium ${
                    currentMode === 'rl' 
                      ? 'bg-green-500 text-white' 
                      : status.rl_available 
                        ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  }`}
                >
                  RL Policy {!status.rl_available && '(Unavailable)'}
                </button>
              </div>
            </div>
            
            {/* Stress Test Controls */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-600">Disruptions:</span>
              <button
                onClick={() => applyStress('closure', { stop_id: 210 })}
                className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600 text-sm"
              >
                Road Closure
              </button>
              <button
                onClick={() => applyStress('traffic', { factor: 2.0 })}
                className="px-3 py-1 bg-yellow-500 text-white rounded hover:bg-yellow-600 text-sm"
              >
                Traffic Jam
              </button>
              <button
                onClick={() => applyStress('surge', { multiplier: 3.0 })}
                className="px-3 py-1 bg-orange-500 text-white rounded hover:bg-orange-600 text-sm"
              >
                Demand Surge
              </button>
              <button
                onClick={resetSimulation}
                className="px-3 py-1 bg-gray-500 text-white rounded hover:bg-gray-600 text-sm"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
        
        {/* Side-by-side Maps */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <BusMap
            title="Static Schedule (Baseline)"
            buses={systemState?.buses?.filter(b => b.mode === 'static') || []}
            stops={systemState?.stops || []}
          />
          <BusMap
            title="RL Policy (Adaptive)"
            buses={systemState?.buses?.filter(b => b.mode === 'rl') || []}
            stops={systemState?.stops || []}
          />
        </div>
        
        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <KPICard
            title="Average Wait Time"
            value={systemState?.kpi?.avg_wait}
            baselineValue={systemState?.baseline_kpi?.avg_wait}
            unit=" min"
            improvement={improvements.avg_wait}
          />
          <KPICard
            title="90th Percentile Wait"
            value={systemState?.kpi?.p90_wait}
            baselineValue={systemState?.baseline_kpi?.p90_wait}
            unit=" min"
          />
          <KPICard
            title="Load Std Dev"
            value={systemState?.kpi?.load_std}
            baselineValue={systemState?.baseline_kpi?.load_std}
            improvement={improvements.overcrowd}
          />
          <KPICard
            title="System Status"
            value={currentMode.toUpperCase()}
            baselineValue={null}
            unit=""
          />
        </div>
        
        {/* Performance Charts */}
        <div className="grid grid-cols-1 gap-6">
          {/* Wait Time Chart */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-4">Wait Time Comparison</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={kpiHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  label={{ value: 'Time (minutes)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  label={{ value: 'Wait Time (minutes)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="baseline_avg_wait" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                  name="Baseline (Static)"
                />
                <Line 
                  type="monotone" 
                  dataKey="rl_avg_wait" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  name="RL Policy"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          {/* Load Distribution Chart */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-4">Load Distribution (Overcrowding)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={kpiHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  label={{ value: 'Time (minutes)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis 
                  label={{ value: 'Load Std Dev', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="baseline_load_std" 
                  stroke="#f59e0b" 
                  strokeWidth={2}
                  name="Baseline"
                />
                <Line 
                  type="monotone" 
                  dataKey="rl_load_std" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  name="RL Policy"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Bus Dispatch RL Demo - Real-time adaptive routing with reinforcement learning</p>
          <p>Green improvements indicate RL is outperforming the baseline static schedule</p>
        </div>
      </div>
    </div>
  );
}