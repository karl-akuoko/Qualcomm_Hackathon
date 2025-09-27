"""
Data adapters for converting between simulation state and API responses.
Handles data transformation and formatting for different clients.
"""

from typing import Dict, List, Any, Optional
import numpy as np
from datetime import datetime


class DataAdapter:
    """Base class for data adapters."""
    
    @staticmethod
    def format_bus_data(bus_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format bus data for API response."""
        return {
            'id': bus_data['id'],
            'x': round(float(bus_data['x']), 2),
            'y': round(float(bus_data['y']), 2),
            'load': bus_data['load'],
            'capacity': bus_data['capacity'],
            'load_ratio': round(bus_data['load'] / bus_data['capacity'], 2),
            'mode': bus_data['mode'],
            'position': {
                'lat': bus_data['x'] / 20.0,  # Normalize to 0-1 for map display
                'lng': bus_data['y'] / 20.0
            }
        }
    
    @staticmethod
    def format_stop_data(stop_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format stop data for API response."""
        return {
            'id': stop_data['id'],
            'x': stop_data['x'],
            'y': stop_data['y'],
            'queue_len': stop_data['queue_len'],
            'demand_level': DataAdapter._get_demand_level(stop_data['queue_len']),
            'position': {
                'lat': stop_data['x'] / 20.0,  # Normalize to 0-1
                'lng': stop_data['y'] / 20.0
            }
        }
    
    @staticmethod
    def _get_demand_level(queue_len: int) -> str:
        """Convert queue length to demand level."""
        if queue_len <= 5:
            return 'low'
        elif queue_len <= 15:
            return 'medium'
        else:
            return 'high'
    
    @staticmethod
    def format_kpi_data(kpi_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format KPI data for API response."""
        return {
            'avg_wait': round(kpi_data.get('avg_wait', 0), 2),
            'p90_wait': round(kpi_data.get('p90_wait', 0), 2),
            'load_std': round(kpi_data.get('load_std', 0), 2),
            'overcrowd_ratio': round(kpi_data.get('overcrowd_ratio', 0), 3),
            'total_replans': kpi_data.get('total_replans', 0),
            'replan_frequency': round(kpi_data.get('replan_frequency', 0), 2),
            'active_riders': kpi_data.get('active_riders', 0),
            'total_arrivals': kpi_data.get('total_arrivals', 0),
            'total_departures': kpi_data.get('total_departures', 0)
        }


class DashboardAdapter(DataAdapter):
    """Adapter for dashboard-specific data formatting."""
    
    @staticmethod
    def format_simulation_state(state: Dict[str, Any]) -> Dict[str, Any]:
        """Format simulation state for dashboard display."""
        return {
            'timestamp': state.get('time', 0),
            'simulation_time': DashboardAdapter._format_simulation_time(state.get('time', 0)),
            'buses': [DashboardAdapter.format_bus_data(bus) for bus in state.get('buses', [])],
            'stops': [DashboardAdapter.format_stop_data(stop) for stop in state.get('stops', [])],
            'kpis': DashboardAdapter.format_kpi_data(state.get('kpis', {})),
            'active_disruptions': state.get('active_disruptions', []),
            'map_bounds': {
                'north': 1.0,
                'south': 0.0,
                'east': 1.0,
                'west': 0.0
            }
        }
    
    @staticmethod
    def _format_simulation_time(seconds: float) -> str:
        """Format simulation time as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def format_comparison_data(baseline_kpis: Dict[str, Any], 
                             rl_kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Format comparison data for dashboard."""
        improvements = {}
        
        for metric in ['avg_wait', 'p90_wait', 'load_std', 'overcrowd_ratio']:
            baseline_val = baseline_kpis.get(metric, 0)
            rl_val = rl_kpis.get(metric, 0)
            
            if baseline_val > 0:
                improvement = ((baseline_val - rl_val) / baseline_val) * 100
                improvements[f'{metric}_improvement'] = round(improvement, 1)
            else:
                improvements[f'{metric}_improvement'] = 0.0
        
        return {
            'baseline': DashboardAdapter.format_kpi_data(baseline_kpis),
            'rl': DashboardAdapter.format_kpi_data(rl_kpis),
            'improvements': improvements
        }


class MobileAdapter(DataAdapter):
    """Adapter for mobile app-specific data formatting."""
    
    @staticmethod
    def format_rider_view(state: Dict[str, Any], user_stop_id: int) -> Dict[str, Any]:
        """Format data for rider mobile app."""
        # Find user's stop
        user_stop = None
        for stop in state.get('stops', []):
            if stop['id'] == user_stop_id:
                user_stop = stop
                break
        
        if not user_stop:
            return {'error': 'Stop not found'}
        
        # Calculate ETAs for buses approaching this stop
        etas = MobileAdapter._calculate_stop_etas(state.get('buses', []), user_stop)
        
        return {
            'stop_info': {
                'id': user_stop['id'],
                'queue_len': user_stop['queue_len'],
                'demand_level': MobileAdapter._get_demand_level(user_stop['queue_len']),
                'position': {
                    'lat': user_stop['x'] / 20.0,
                    'lng': user_stop['y'] / 20.0
                }
            },
            'etas': etas,
            'nearby_buses': MobileAdapter._get_nearby_buses(state.get('buses', []), user_stop),
            'rl_savings': MobileAdapter._calculate_rl_savings(state.get('kpis', {}))
        }
    
    @staticmethod
    def _calculate_stop_etas(buses: List[Dict[str, Any]], target_stop: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Calculate ETAs for buses approaching a stop."""
        etas = []
        
        for bus in buses:
            # Simple distance-based ETA calculation
            distance = np.sqrt((bus['x'] - target_stop['x'])**2 + (bus['y'] - target_stop['y'])**2)
            eta_seconds = distance * 30  # Assume 30 seconds per grid unit
            
            if eta_seconds <= 600:  # Only show buses within 10 minutes
                etas.append({
                    'bus_id': bus['id'],
                    'eta_seconds': int(eta_seconds),
                    'eta_minutes': int(eta_seconds // 60),
                    'load_ratio': round(bus['load'] / bus['capacity'], 2),
                    'has_space': bus['load'] < bus['capacity']
                })
        
        # Sort by ETA
        etas.sort(key=lambda x: x['eta_seconds'])
        return etas[:5]  # Return top 5
    
    @staticmethod
    def _get_nearby_buses(buses: List[Dict[str, Any]], target_stop: Dict[str, Any], 
                         max_distance: float = 3.0) -> List[Dict[str, Any]]:
        """Get buses near a stop."""
        nearby = []
        
        for bus in buses:
            distance = np.sqrt((bus['x'] - target_stop['x'])**2 + (bus['y'] - target_stop['y'])**2)
            if distance <= max_distance:
                nearby.append({
                    'id': bus['id'],
                    'distance': round(distance, 2),
                    'load_ratio': round(bus['load'] / bus['capacity'], 2),
                    'position': {
                        'lat': bus['x'] / 20.0,
                        'lng': bus['y'] / 20.0
                    }
                })
        
        return nearby
    
    @staticmethod
    def _calculate_rl_savings(kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate RL savings for display."""
        # This would typically compare with baseline, but for demo purposes
        # we'll use some mock calculations
        avg_wait = kpis.get('avg_wait', 0)
        
        if avg_wait > 0:
            # Mock improvement calculation
            improvement_percent = min(25, max(5, 30 - avg_wait * 2))
            savings_minutes = avg_wait * (improvement_percent / 100)
            
            return {
                'improvement_percent': round(improvement_percent, 1),
                'savings_minutes': round(savings_minutes, 1),
                'status': 'active' if improvement_percent > 15 else 'limited'
            }
        else:
            return {
                'improvement_percent': 0,
                'savings_minutes': 0,
                'status': 'inactive'
            }


class WebSocketAdapter:
    """Adapter for WebSocket message formatting."""
    
    @staticmethod
    def format_live_update(state: Dict[str, Any], update_type: str = "full") -> Dict[str, Any]:
        """Format live update message for WebSocket."""
        return {
            'type': update_type,
            'timestamp': datetime.now().isoformat(),
            'simulation_time': state.get('time', 0),
            'data': {
                'buses': [DataAdapter.format_bus_data(bus) for bus in state.get('buses', [])],
                'stops': [DataAdapter.format_stop_data(stop) for stop in state.get('stops', [])],
                'kpis': DataAdapter.format_kpi_data(state.get('kpis', {})),
                'active_disruptions': state.get('active_disruptions', [])
            }
        }
    
    @staticmethod
    def format_kpi_update(kpis: Dict[str, Any]) -> Dict[str, Any]:
        """Format KPI-only update for WebSocket."""
        return {
            'type': 'kpi_update',
            'timestamp': datetime.now().isoformat(),
            'kpis': DataAdapter.format_kpi_data(kpis)
        }
    
    @staticmethod
    def format_disruption_alert(disruption: Dict[str, Any]) -> Dict[str, Any]:
        """Format disruption alert for WebSocket."""
        return {
            'type': 'disruption_alert',
            'timestamp': datetime.now().isoformat(),
            'disruption': disruption
        }
    
    @staticmethod
    def format_mode_change(mode: str) -> Dict[str, Any]:
        """Format mode change notification for WebSocket."""
        return {
            'type': 'mode_change',
            'timestamp': datetime.now().isoformat(),
            'mode': mode,
            'message': f"Switched to {mode.upper()} mode"
        }
