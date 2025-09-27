import React from 'react';
import { Play, Pause, RotateCcw, Zap, AlertTriangle, Users, Car } from 'lucide-react';

function ControlPanel({ 
  isRunning, 
  mode, 
  onStart, 
  onStop, 
  onReset, 
  onModeChange, 
  onStressTest 
}) {
  return (
    <div className="control-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2rem', fontWeight: '600', color: '#374151' }}>
          Simulation Controls
        </h2>
        <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
          Snapdragon X Elite | On-Device Inference
        </div>
      </div>
      
      <div className="control-buttons">
        {/* Mode Controls */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: '500', color: '#374151' }}>
            Mode:
          </label>
          <button
            className={`btn ${mode === 'static' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => onModeChange('static')}
            disabled={isRunning}
          >
            Static
          </button>
          <button
            className={`btn ${mode === 'rl' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => onModeChange('rl')}
            disabled={isRunning}
          >
            RL Policy
          </button>
        </div>

        {/* Simulation Controls */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {!isRunning ? (
            <button
              className="btn btn-success"
              onClick={onStart}
              disabled={!mode}
            >
              <Play size={16} />
              Start
            </button>
          ) : (
            <button
              className="btn btn-danger"
              onClick={onStop}
            >
              <Pause size={16} />
              Stop
            </button>
          )}
          
          <button
            className="btn btn-secondary"
            onClick={onReset}
          >
            <RotateCcw size={16} />
            Reset
          </button>
        </div>

        {/* Stress Test Controls */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.9rem', fontWeight: '500', color: '#374151' }}>
            Stress Tests:
          </label>
          <button
            className="btn btn-warning"
            onClick={() => onStressTest('closure')}
            disabled={!isRunning}
            title="Close a central road to test resilience"
          >
            <AlertTriangle size={16} />
            Road Closure
          </button>
          <button
            className="btn btn-warning"
            onClick={() => onStressTest('traffic')}
            disabled={!isRunning}
            title="Create traffic slowdown"
          >
            <Car size={16} />
            Traffic Jam
          </button>
          <button
            className="btn btn-warning"
            onClick={() => onStressTest('surge')}
            disabled={!isRunning}
            title="Create demand surge at stadium"
          >
            <Users size={16} />
            Demand Surge
          </button>
        </div>
      </div>

      {/* Demo Script Reminder */}
      <div style={{ 
        marginTop: '1rem', 
        padding: '1rem', 
        background: '#f0f9ff', 
        border: '1px solid #bae6fd', 
        borderRadius: '6px',
        fontSize: '0.85rem',
        color: '#0369a1'
      }}>
        <strong>Demo Script:</strong> Start with Static → Show rising wait times → 
        Switch to RL → Show improvement → Trigger disruptions → Compare resilience
      </div>
    </div>
  );
}

export default ControlPanel;