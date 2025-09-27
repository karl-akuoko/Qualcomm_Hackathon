import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, Settings, Wifi, WifiOff } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import MapView from './components/MapView';
import KPICards from './components/KPICards';
import ControlPanel from './components/ControlPanel';

const API_BASE = '/api';
const WS_URL = 'ws://localhost:8000/ws/live';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [mode, setMode] = useState('static');
  const [simulationData, setSimulationData] = useState(null);
  const [baselineKPIs, setBaselineKPIs] = useState({});
  const [rlKPIs, setRlKPIs] = useState({});
  const [chartData, setChartData] = useState([]);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const chartDataRef = useRef([]);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      wsRef.current = new WebSocket(WS_URL);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setSimulationData(data);
          
          // Update KPIs based on mode
          if (data.kpis) {
            if (mode === 'static') {
              setBaselineKPIs(data.kpis);
            } else {
              setRlKPIs(data.kpis);
            }
          }
          
          // Update chart data
          updateChartData(data);
        } catch (err) {
          console.error('Error parsing WebSocket data:', err);
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error');
        setIsConnected(false);
      };
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('Failed to connect to server');
    }
  };

  const updateChartData = (data) => {
    if (!data.kpis) return;
    
    const newDataPoint = {
      time: new Date().toLocaleTimeString(),
      timestamp: Date.now(),
      avgWait: data.kpis.avg_wait || 0,
      p90Wait: data.kpis.p90_wait || 0,
      loadStd: data.kpis.load_std || 0,
    };
    
    chartDataRef.current = [...chartDataRef.current, newDataPoint].slice(-50); // Keep last 50 points
    setChartData(chartDataRef.current);
  };

  // API calls
  const apiCall = async (endpoint, method = 'GET', data = null) => {
    try {
      const options = {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
      };
      
      if (data) {
        options.body = JSON.stringify(data);
      }
      
      const response = await fetch(`${API_BASE}${endpoint}`, options);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (err) {
      console.error(`API call failed:`, err);
      setError(err.message);
      throw err;
    }
  };

  // Control functions
  const startSimulation = async () => {
    try {
      await apiCall('/start', 'POST');
      setIsRunning(true);
      setError(null);
    } catch (err) {
      console.error('Failed to start simulation:', err);
    }
  };

  const stopSimulation = async () => {
    try {
      await apiCall('/stop', 'POST');
      setIsRunning(false);
      setError(null);
    } catch (err) {
      console.error('Failed to stop simulation:', err);
    }
  };

  const resetSimulation = async () => {
    try {
      await apiCall('/reset', 'POST', { seed: 42 });
      setChartData([]);
      chartDataRef.current = [];
      setError(null);
    } catch (err) {
      console.error('Failed to reset simulation:', err);
    }
  };

  const switchMode = async (newMode) => {
    try {
      await apiCall('/mode', 'POST', { mode: newMode });
      setMode(newMode);
      setError(null);
    } catch (err) {
      console.error('Failed to switch mode:', err);
    }
  };

  const triggerStress = async (type) => {
    try {
      await apiCall('/stress', 'POST', { type });
      setError(null);
    } catch (err) {
      console.error('Failed to trigger stress test:', err);
    }
  };

  const getStatus = async () => {
    try {
      const status = await apiCall('/status');
      setIsRunning(status.is_running);
      setMode(status.mode);
      return status;
    } catch (err) {
      console.error('Failed to get status:', err);
      return null;
    }
  };

  // Initialize status on mount
  useEffect(() => {
    getStatus();
  }, []);

  return (
    <div className="dashboard">
      <header className="header">
        <h1>🚌 Bus Routing Dashboard</h1>
        <p>RL-driven dispatcher vs Fixed schedule comparison</p>
        <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div className={`status-indicator ${isConnected ? 'online' : 'offline'}`}>
            {isConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
          <div className={`status-indicator ${mode === 'rl' ? 'rl' : 'static'}`}>
            Mode: {mode.toUpperCase()}
          </div>
          {isRunning && (
            <div className="status-indicator online">
              <div className="pulse" style={{ width: 8, height: 8, backgroundColor: '#10b981', borderRadius: '50%', marginRight: '0.5rem' }}></div>
              Running
            </div>
          )}
        </div>
      </header>

      <main className="main-content">
        <ControlPanel
          isRunning={isRunning}
          mode={mode}
          onStart={startSimulation}
          onStop={stopSimulation}
          onReset={resetSimulation}
          onModeChange={switchMode}
          onStressTest={triggerStress}
        />

        <div className="map-container">
          <h3>Static Schedule (Baseline)</h3>
          <MapView 
            data={mode === 'static' ? simulationData : null}
            mode="static"
          />
        </div>

        <div className="map-container">
          <h3>RL Policy</h3>
          <MapView 
            data={mode === 'rl' ? simulationData : null}
            mode="rl"
          />
        </div>

        <KPICards
          baselineKPIs={baselineKPIs}
          rlKPIs={rlKPIs}
          currentKPIs={simulationData?.kpis}
          mode={mode}
        />

        <div className="kpi-panel">
          <h3>Performance Trends</h3>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                  interval="preserveStartEnd"
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  formatter={(value, name) => [value.toFixed(2), name]}
                  labelFormatter={(label) => `Time: ${label}`}
                />
                <Line 
                  type="monotone" 
                  dataKey="avgWait" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false}
                  name="Avg Wait (s)"
                />
                <Line 
                  type="monotone" 
                  dataKey="p90Wait" 
                  stroke="#f59e0b" 
                  strokeWidth={2}
                  dot={false}
                  name="P90 Wait (s)"
                />
                <Line 
                  type="monotone" 
                  dataKey="loadStd" 
                  stroke="#10b981" 
                  strokeWidth={2}
                  dot={false}
                  name="Load Std Dev"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>

      {error && (
        <div style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          background: '#fee2e2',
          color: '#991b1b',
          padding: '1rem',
          borderRadius: '6px',
          border: '1px solid #fecaca',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          zIndex: 1000
        }}>
          <strong>Error:</strong> {error}
          <button 
            onClick={() => setError(null)}
            style={{
              marginLeft: '1rem',
              background: 'none',
              border: 'none',
              color: '#991b1b',
              cursor: 'pointer'
            }}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

export default App;