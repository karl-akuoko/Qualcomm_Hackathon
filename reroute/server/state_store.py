"""
State store for managing simulation state and persistence
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import threading

@dataclass
class SimulationSnapshot:
    """Snapshot of simulation state at a point in time"""
    timestamp: float
    time: float
    mode: str
    buses: List[Dict[str, Any]]
    stops: List[Dict[str, Any]]
    kpi: Dict[str, float]
    baseline_kpi: Dict[str, float]
    improvements: Dict[str, float]

class StateStore:
    """Thread-safe state store for simulation data"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.current_state: Optional[SimulationSnapshot] = None
        self.history: List[SimulationSnapshot] = []
        self.lock = threading.Lock()
        
        # Performance metrics
        self.metrics_history: List[Dict[str, Any]] = []
        self.episode_stats: Dict[str, Any] = {}
        
    def update_state(self, state_data: Dict[str, Any]):
        """Update current state with new simulation data"""
        with self.lock:
            snapshot = SimulationSnapshot(
                timestamp=time.time(),
                time=state_data.get('time', 0.0),
                mode=state_data.get('mode', 'static'),
                buses=state_data.get('buses', []),
                stops=state_data.get('stops', []),
                kpi=state_data.get('kpi', {}),
                baseline_kpi=state_data.get('baseline_kpi', {}),
                improvements=state_data.get('improvements', {})
            )
            
            self.current_state = snapshot
            self.history.append(snapshot)
            
            # Keep only recent history
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
    
    def get_current_state(self) -> Optional[SimulationSnapshot]:
        """Get current simulation state"""
        with self.lock:
            return self.current_state
    
    def get_history(self, limit: Optional[int] = None) -> List[SimulationSnapshot]:
        """Get state history"""
        with self.lock:
            if limit:
                return self.history[-limit:]
            return self.history.copy()
    
    def get_metrics_trend(self, metric_name: str, window: int = 50) -> List[float]:
        """Get trend data for a specific metric"""
        with self.lock:
            recent_states = self.history[-window:] if len(self.history) >= window else self.history
            
            values = []
            for state in recent_states:
                if metric_name in state.kpi:
                    values.append(state.kpi[metric_name])
                elif metric_name in state.baseline_kpi:
                    values.append(state.baseline_kpi[metric_name])
                else:
                    values.append(0.0)
            
            return values
    
    def calculate_improvements(self) -> Dict[str, float]:
        """Calculate performance improvements over time"""
        with self.lock:
            if not self.current_state:
                return {}
            
            current = self.current_state
            improvements = {}
            
            # Calculate improvements from current state
            if current.baseline_kpi and current.kpi:
                baseline_avg_wait = current.baseline_kpi.get('avg_wait', 0)
                rl_avg_wait = current.kpi.get('avg_wait', 0)
                
                if baseline_avg_wait > 0:
                    improvements['avg_wait'] = (baseline_avg_wait - rl_avg_wait) / baseline_avg_wait
                
                baseline_load_std = current.baseline_kpi.get('load_std', 0)
                rl_load_std = current.kpi.get('load_std', 0)
                
                if baseline_load_std > 0:
                    improvements['overcrowd'] = (baseline_load_std - rl_load_std) / baseline_load_std
            
            return improvements
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            if not self.current_state:
                return {}
            
            current = self.current_state
            improvements = self.calculate_improvements()
            
            # Calculate rolling averages
            recent_states = self.history[-20:] if len(self.history) >= 20 else self.history
            
            avg_wait_trend = []
            load_std_trend = []
            
            for state in recent_states:
                if state.kpi:
                    avg_wait_trend.append(state.kpi.get('avg_wait', 0))
                    load_std_trend.append(state.kpi.get('load_std', 0))
            
            return {
                'current_time': current.time,
                'mode': current.mode,
                'current_metrics': current.kpi,
                'baseline_metrics': current.baseline_kpi,
                'improvements': improvements,
                'trends': {
                    'avg_wait': avg_wait_trend,
                    'load_std': load_std_trend
                },
                'total_snapshots': len(self.history),
                'simulation_duration': current.time
            }
    
    def reset(self):
        """Reset state store"""
        with self.lock:
            self.current_state = None
            self.history.clear()
            self.metrics_history.clear()
            self.episode_stats.clear()
    
    def export_data(self, filepath: str):
        """Export state data to JSON file"""
        with self.lock:
            export_data = {
                'current_state': asdict(self.current_state) if self.current_state else None,
                'history': [asdict(state) for state in self.history],
                'metrics_history': self.metrics_history,
                'episode_stats': self.episode_stats
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
    
    def import_data(self, filepath: str):
        """Import state data from JSON file"""
        with self.lock:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            if data.get('current_state'):
                self.current_state = SimulationSnapshot(**data['current_state'])
            
            self.history = [SimulationSnapshot(**state) for state in data.get('history', [])]
            self.metrics_history = data.get('metrics_history', [])
            self.episode_stats = data.get('episode_stats', {})

# Global state store instance
state_store = StateStore()
