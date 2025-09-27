import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface SimulationData {
  buses: Array<{
    id: number;
    x: number;
    y: number;
    load: number;
    capacity: number;
    mode: string;
  }>;
  stops: Array<{
    id: number;
    x: number;
    y: number;
    queue_len: number;
  }>;
  kpis: {
    avg_wait: number;
    p90_wait: number;
    load_std: number;
    overcrowd_ratio: number;
    active_riders: number;
  };
  time: number;
}

interface WebSocketContextType {
  isConnected: boolean;
  simulationData: SimulationData | null;
  error: string | null;
  connect: () => void;
  disconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

const WS_URL = 'ws://localhost:8000/ws/live'; // In production, use actual server URL

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [simulationData, setSimulationData] = useState<SimulationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      setError(null);
      const websocket = new WebSocket(WS_URL);

      websocket.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setReconnectAttempts(0);
        setError(null);
      };

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setSimulationData(data);
        } catch (err) {
          console.error('Error parsing WebSocket data:', err);
          setError('Failed to parse server data');
        }
      };

      websocket.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, delay);
        } else {
          setError('Connection lost. Please check your internet connection.');
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error');
        setIsConnected(false);
      };

      setWs(websocket);
    } catch (err) {
      console.error('Failed to connect WebSocket:', err);
      setError('Failed to connect to server');
    }
  };

  const disconnect = () => {
    if (ws) {
      ws.close();
      setWs(null);
    }
    setIsConnected(false);
    setReconnectAttempts(maxReconnectAttempts); // Prevent auto-reconnect
  };

  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, []);

  const value: WebSocketContextType = {
    isConnected,
    simulationData,
    error,
    connect,
    disconnect,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};