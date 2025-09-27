"""
State management and data persistence for the simulation server.
Handles KPI history, configuration, and demo data storage.
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import numpy as np
import os


@dataclass
class KPIRecord:
    """Single KPI measurement record."""
    timestamp: float
    avg_wait: float
    p90_wait: float
    load_std: float
    overcrowd_ratio: float
    total_replans: int
    replan_frequency: float
    total_reward: float
    mode: str


@dataclass
class SimulationConfig:
    """Simulation configuration."""
    grid_size: int = 20
    num_buses: int = 6
    num_stops: int = 35
    bus_capacity: int = 50
    seed: int = 42
    mode: str = "static"
    simulation_rate_hz: float = 10.0
    update_rate_hz: float = 5.0


class StateStore:
    """Manages simulation state and data persistence."""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.config_file = os.path.join(data_dir, "config.json")
        self.kpi_history_file = os.path.join(data_dir, "kpi_history.json")
        self.demo_file = os.path.join(data_dir, "demo_data.json")
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize storage
        self.kpi_history: List[KPIRecord] = []
        self.config = SimulationConfig()
        self.demo_data: Dict[str, Any] = {}
        
        # Load existing data
        self.load_config()
        self.load_kpi_history()
        self.load_demo_data()
        
        # Rolling windows for real-time calculations
        self.rolling_window_size = 100
        self.recent_kpis: List[KPIRecord] = []
    
    def save_config(self):
        """Save current configuration."""
        config_dict = asdict(self.config)
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def load_config(self):
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_dict = json.load(f)
                self.config = SimulationConfig(**config_dict)
            except Exception as e:
                print(f"Failed to load config: {e}")
                self.config = SimulationConfig()
    
    def update_config(self, **kwargs):
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save_config()
    
    def add_kpi_record(self, kpi_data: Dict[str, Any], mode: str, total_reward: float = 0.0):
        """Add a new KPI record."""
        record = KPIRecord(
            timestamp=time.time(),
            avg_wait=kpi_data.get('avg_wait', 0.0),
            p90_wait=kpi_data.get('p90_wait', 0.0),
            load_std=kpi_data.get('load_std', 0.0),
            overcrowd_ratio=kpi_data.get('overcrowd_ratio', 0.0),
            total_replans=kpi_data.get('total_replans', 0),
            replan_frequency=kpi_data.get('replan_frequency', 0.0),
            total_reward=total_reward,
            mode=mode
        )
        
        self.kpi_history.append(record)
        self.recent_kpis.append(record)
        
        # Maintain rolling window
        if len(self.recent_kpis) > self.rolling_window_size:
            self.recent_kpis.pop(0)
        
        # Save periodically (every 10 records)
        if len(self.kpi_history) % 10 == 0:
            self.save_kpi_history()
    
    def save_kpi_history(self):
        """Save KPI history to file."""
        # Convert to serializable format
        history_dict = [asdict(record) for record in self.kpi_history]
        
        with open(self.kpi_history_file, 'w') as f:
            json.dump(history_dict, f, indent=2)
    
    def load_kpi_history(self):
        """Load KPI history from file."""
        if os.path.exists(self.kpi_history_file):
            try:
                with open(self.kpi_history_file, 'r') as f:
                    history_dict = json.load(f)
                self.kpi_history = [KPIRecord(**record) for record in history_dict]
                
                # Initialize recent KPIs with last N records
                self.recent_kpis = self.kpi_history[-self.rolling_window_size:]
                
            except Exception as e:
                print(f"Failed to load KPI history: {e}")
                self.kpi_history = []
                self.recent_kpis = []
    
    def get_kpi_summary(self, mode: str = None, time_window_minutes: int = 5) -> Dict[str, float]:
        """Get KPI summary for specified mode and time window."""
        cutoff_time = time.time() - (time_window_minutes * 60)
        
        # Filter records
        if mode:
            records = [r for r in self.recent_kpis if r.mode == mode and r.timestamp >= cutoff_time]
        else:
            records = [r for r in self.recent_kpis if r.timestamp >= cutoff_time]
        
        if not records:
            return {}
        
        # Calculate statistics
        summary = {
            'avg_wait_mean': np.mean([r.avg_wait for r in records]),
            'avg_wait_std': np.std([r.avg_wait for r in records]),
            'p90_wait_mean': np.mean([r.p90_wait for r in records]),
            'p90_wait_std': np.std([r.p90_wait for r in records]),
            'load_std_mean': np.mean([r.load_std for r in records]),
            'overcrowd_ratio_mean': np.mean([r.overcrowd_ratio for r in records]),
            'replan_frequency_mean': np.mean([r.replan_frequency for r in records]),
            'total_reward_mean': np.mean([r.total_reward for r in records]),
            'sample_count': len(records)
        }
        
        return summary
    
    def get_performance_comparison(self, time_window_minutes: int = 5) -> Dict[str, Any]:
        """Compare performance between modes."""
        baseline_summary = self.get_kpi_summary('static', time_window_minutes)
        rl_summary = self.get_kpi_summary('rl', time_window_minutes)
        
        if not baseline_summary or not rl_summary:
            return {}
        
        # Calculate improvements
        improvements = {}
        for metric in ['avg_wait_mean', 'p90_wait_mean', 'load_std_mean', 'overcrowd_ratio_mean']:
            baseline_val = baseline_summary.get(metric, 0)
            rl_val = rl_summary.get(metric, 0)
            
            if baseline_val > 0:
                improvement = ((baseline_val - rl_val) / baseline_val) * 100
                improvements[metric.replace('_mean', '_improvement')] = improvement
        
        return {
            'baseline': baseline_summary,
            'rl': rl_summary,
            'improvements': improvements,
            'time_window_minutes': time_window_minutes
        }
    
    def save_demo_data(self, demo_name: str, demo_data: Dict[str, Any]):
        """Save demo data for playback."""
        self.demo_data[demo_name] = {
            'timestamp': time.time(),
            'data': demo_data
        }
        
        with open(self.demo_file, 'w') as f:
            json.dump(self.demo_data, f, indent=2)
    
    def load_demo_data(self):
        """Load demo data."""
        if os.path.exists(self.demo_file):
            try:
                with open(self.demo_file, 'r') as f:
                    self.demo_data = json.load(f)
            except Exception as e:
                print(f"Failed to load demo data: {e}")
                self.demo_data = {}
    
    def get_demo_data(self, demo_name: str) -> Optional[Dict[str, Any]]:
        """Get saved demo data."""
        return self.demo_data.get(demo_name, {}).get('data')
    
    def list_demos(self) -> List[str]:
        """List available demo names."""
        return list(self.demo_data.keys())
    
    def get_kpi_trends(self, metric: str, time_window_hours: int = 1) -> Dict[str, List]:
        """Get KPI trends for visualization."""
        cutoff_time = time.time() - (time_window_hours * 3600)
        
        # Filter recent records
        recent_records = [r for r in self.kpi_history if r.timestamp >= cutoff_time]
        
        if not recent_records:
            return {'timestamps': [], 'values': [], 'modes': []}
        
        # Extract data
        timestamps = [r.timestamp for r in recent_records]
        values = [getattr(r, metric, 0) for r in recent_records]
        modes = [r.mode for r in recent_records]
        
        return {
            'timestamps': timestamps,
            'values': values,
            'modes': modes
        }
    
    def clear_old_data(self, days_to_keep: int = 7):
        """Clear old data to manage storage."""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        # Filter KPI history
        original_count = len(self.kpi_history)
        self.kpi_history = [r for r in self.kpi_history if r.timestamp >= cutoff_time]
        self.recent_kpis = [r for r in self.recent_kpis if r.timestamp >= cutoff_time]
        
        removed_count = original_count - len(self.kpi_history)
        if removed_count > 0:
            print(f"Cleared {removed_count} old KPI records")
            self.save_kpi_history()
    
    def export_data(self, export_path: str):
        """Export all data to a file."""
        export_data = {
            'config': asdict(self.config),
            'kpi_history': [asdict(record) for record in self.kpi_history],
            'demo_data': self.demo_data,
            'export_timestamp': time.time(),
            'total_records': len(self.kpi_history)
        }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"Data exported to {export_path}")


# Global state store instance
state_store = StateStore()


def get_state_store() -> StateStore:
    """Get global state store instance."""
    return state_store
