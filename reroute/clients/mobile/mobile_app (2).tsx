import React, { useState, useEffect, useRef } from 'react';
import { MapPin, Clock, Zap, Users, Navigation } from 'lucide-react';

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/live';

// ETA Display Component
const ETACard = ({ stop, eta, isRLMode }) => {
  const getETAColor = (minutes) => {
    if (minutes <= 2) return 'text-green-600';
    if (minutes <= 5) return 'text-yellow-600';
    return 'text-red-600';
  };
  
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-3 border-l-4 border-blue-500">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <MapPin className="w-5 h-5 text-gray-500" />
          <div>
            <h4 className="font-semibold text-gray-900">Stop {stop.id}</h4>
            <p className="text-sm text-gray-500">
              Grid: ({stop.x}, {stop.y}) • Queue: {stop.queue_len} riders
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${getETAColor(eta)}`}>
            {eta}
            <span className="text-sm text-gray-500 ml-1">min</span>
          </div>
          {stop.queue_len > 0 && (
            <div className="flex items-center gap-1 mt-1">
              <Users className="w-3 h-3 text-gray-400" />
              <span className="text-xs text-gray-500">
                {stop.queue_len} waiting
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// RL Savings Badge
const RLSavingsBadge = ({ improvement }) => {
  if (!improvement || improvement <= 0) return null;
  
  const improvementPercent = improvement * 100;
  
  return (
    <div className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg p-4 mb-4 text-white">
      <div className="flex items-center gap-3">
        <div className="bg-white/20 rounded-full p-2">
          <Zap className="w-6 h-6" />
        </div>
        <div>
          <h3 className="font-bold text-lg">RL Mode Active</h3>
          <p className="text-green-100">
            {improvementPercent.toFixed(1)}% faster wait times vs static schedule
          </p>
        </div>
      </div>
    </div>
  );
};

// Bus Location Indicator
const NearbyBuses = ({ buses, selectedStop }) => {
  if (!buses || !selectedStop) return null;
  
  // Calculate distances to selected stop
  const busesWithDistance = buses.map(bus => {
    const distance = Math.sqrt(
      Math.pow(bus.x - selectedStop.x, 2) + Math.pow(bus.y - selectedStop.y, 2)
    );
    return { ...bus, distance };
  }).sort((a, b) => a.distance - b.distance);
  
  const nearbyBuses = busesWithDistance.slice(0, 3); // Show closest 3 buses
  
  return (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
      <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
        <Navigation className="w-4 h-4" />
        Nearby Buses
      </h3>
      <div className="space-y-2">
        {nearbyBuses.map(bus => (
          <div key={bus.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${
                bus.is_moving ? 'bg-blue-500' : 'bg-gray-400'
              }`}></div>
              <span className="font-medium">Bus {bus.id}</span>
            </div>
            <div className="text-right text-sm">
              <div className="font-medium">
                {bus.distance.toFixed(1)} blocks away
              </div>
              <div className="text-gray-500">
                {bus.load}/{bus.capacity} passengers
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// Main Rider App Component
export default function RiderApp() {
  const [systemState, setSystemState] = useState(null);
  const [selectedStop, setSelectedStop] = useState(null);
  const [nearbyStops, setNearbyStops] = useState([]);
  const [currentMode, setCurrentMode] = useState('static');
  const [improvements, setImprovements] = useState({});
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
            
            // Calculate improvements
            if (state.kpi && state.baseline_kpi) {
              const avgWaitImprovement = state.baseline_kpi.avg_wait > 0 
                ? (state.baseline_kpi.avg_wait - state.kpi.avg_wait) / state.baseline_kpi.avg_wait 
                : 0;
              
              setImprovements({ avg_wait: avgWaitImprovement });
            }
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
  
  // Get system status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        setCurrentMode(data.mode);
      } catch (error) {
        console.error('Error fetching status:', error);
      }
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);
  
  // Initialize with a popular stop
  useEffect(() => {
    if (systemState?.stops && !selectedStop) {
      // Find a stop with decent activity
      const activeStops = systemState.stops
        .filter(stop => stop.queue_len > 0)
        .sort((a, b) => b.queue_len - a.queue_len);
      
      if (activeStops.length > 0) {
        setSelectedStop(activeStops[0]);
      } else if (systemState.stops.length > 0) {
        // Fallback to first stop
        setSelectedStop(systemState.stops[0]);
      }
    }
  }, [systemState?.stops, selectedStop]);
  
  // Update nearby stops when selection changes
  useEffect(() => {
    if (selectedStop && systemState?.stops) {
      const others = systemState.stops
        .filter(stop => stop.id !== selectedStop.id)
        .map(stop => {
          const distance = Math.sqrt(
            Math.pow(stop.x - selectedStop.x, 2) + Math.pow(stop.y - selectedStop.y, 2)
          );
          return { ...stop, distance };
        })
        .sort((a, b) => a.distance - b.distance)
        .slice(0, 5); // Show 5 nearest stops
      
      setNearbyStops(others);
    }
  }, [selectedStop, systemState?.stops]);
  
  // Calculate ETA for selected stop
  const calculateETA = (stop) => {
    if (!systemState?.buses) return 12; // Default ETA
    
    const nearestBus = systemState.buses
      .map(bus => {
        const distance = Math.sqrt(
          Math.pow(bus.x - stop.x, 2) + Math.pow(bus.y - stop.y, 2)
        );
        return { ...bus, distance };
      })
      .sort((a, b) => a.distance - b.distance)[0];
    
    if (!nearestBus) return 12;
    
    // Estimate ETA based on distance and if bus is moving
    const baseTime = nearestBus.distance * 0.5; // ~30 seconds per block
    const movementFactor = nearestBus.is_moving ? 1.0 : 1.5;
    const loadFactor = 1 + (nearestBus.load / nearestBus.capacity) * 0.3; // Slower when full
    
    return Math.max(1, Math.round(baseTime * movementFactor * loadFactor));
  };
  
  const selectedStopETA = selectedStop ? calculateETA(selectedStop) : 0;
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">Bus Tracker</h1>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="text-sm text-gray-600">
                {currentMode.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="max-w-md mx-auto p-4">
        {/* RL Savings Badge */}
        {currentMode === 'rl' && (
          <RLSavingsBadge improvement={improvements.avg_wait} />
        )}
        
        {/* Selected Stop */}
        {selectedStop && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">
              Your Stop
            </h2>
            <div className="bg-white rounded-xl shadow-lg p-6 border-2 border-blue-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">
                    Stop {selectedStop.id}
                  </h3>
                  <p className="text-gray-500">
                    Location: ({selectedStop.x}, {selectedStop.y})
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-blue-600">
                    {selectedStopETA}
                    <span className="text-lg text-gray-500 ml-1">min</span>
                  </div>
                  <p className="text-sm text-gray-500">Next bus</p>
                </div>
              </div>
              
              {selectedStop.queue_len > 0 && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-gray-500" />
                    <span className="text-sm text-gray-700">
                      {selectedStop.queue_len} people waiting
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Nearby Buses */}
        <NearbyBuses buses={systemState?.buses} selectedStop={selectedStop} />
        
        {/* Nearby Stops */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Other Nearby Stops
          </h3>
          <div className="space-y-2">
            {nearbyStops.map(stop => (
              <button
                key={stop.id}
                onClick={() => setSelectedStop(stop)}
                className="w-full text-left"
              >
                <ETACard
                  stop={stop}
                  eta={calculateETA(stop)}
                  isRLMode={currentMode === 'rl'}
                />
              </button>
            ))}
          </div>
        </div>
        
        {/* System Info */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <h3 className="font-semibold text-gray-900 mb-3">System Status</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Mode:</span>
              <div className={`font-semibold ${
                currentMode === 'rl' ? 'text-green-600' : 'text-blue-600'
              }`}>
                {currentMode === 'rl' ? 'Smart Routing' : 'Fixed Schedule'}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Active Buses:</span>
              <div className="font-semibold text-gray-900">
                {systemState?.buses?.length || 0}
              </div>
            </div>
            <div>
              <span className="text-gray-500">Avg Wait:</span>
              <div className="font-semibold text-gray-900">
                {systemState?.kpi?.avg_wait?.toFixed(1) || 0} min
              </div>
            </div>
            <div>
              <span className="text-gray-500">Total Stops:</span>
              <div className="font-semibold text-gray-900">
                {systemState?.stops?.length || 0}
              </div>
            </div>
          </div>
          
          {currentMode === 'rl' && improvements.avg_wait > 0 && (
            <div className="mt-3 p-3 bg-green-50 rounded-lg">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-green-600" />
                <span className="text-sm text-green-800 font-medium">
                  Smart routing is {(improvements.avg_wait * 100).toFixed(1)}% faster
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}