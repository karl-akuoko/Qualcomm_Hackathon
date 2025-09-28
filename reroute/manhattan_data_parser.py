#!/usr/bin/env python3
"""
Parse Manhattan bus data and create realistic bus dispatch system
"""

import json
import csv
import os
import sys
import math
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

@dataclass
class ManhattanStop:
    """Real Manhattan bus stop"""
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    routes: List[str]
    x: int  # Grid position
    y: int  # Grid position
    wheelchair_boarding: bool = False

@dataclass
class ManhattanRoute:
    """Real MTA bus route"""
    route_id: str
    route_name: str
    stops: List[str]  # Stop IDs in order
    direction: str  # NB, SB, EB, WB
    color: str = "#3b82f6"

class ManhattanDataParser:
    """Parse and process Manhattan bus data"""
    
    def __init__(self, data_dir: str = "UI_data"):
        self.data_dir = data_dir
        self.stops: Dict[str, ManhattanStop] = {}
        self.routes: Dict[str, ManhattanRoute] = {}
        
        # Manhattan bounds (approximate)
        self.min_lat = 40.7000
        self.max_lat = 40.8200
        self.min_lon = -74.0500
        self.max_lon = -73.9000
        
        # Grid size for simulation
        self.grid_width = 100
        self.grid_height = 100
    
    def lat_lon_to_grid(self, lat: float, lon: float) -> Tuple[int, int]:
        """Convert lat/lon to grid coordinates"""
        x = int((lon - self.min_lon) / (self.max_lon - self.min_lon) * self.grid_width)
        y = int((lat - self.min_lat) / (self.max_lat - self.min_lat) * self.grid_height)
        
        # Clamp to grid bounds
        x = max(0, min(self.grid_width - 1, x))
        y = max(0, min(self.grid_height - 1, y))
        
        return x, y
    
    def load_manhattan_stops(self) -> Dict[str, ManhattanStop]:
        """Load Manhattan bus stops from data files"""
        print("🗽 Loading Manhattan bus stops...")
        
        # Create sample Manhattan stops based on real MTA data
        manhattan_stops = [
            # Major north-south routes
            {"stop_id": "M1_001", "stop_name": "Central Park S & 5 Av", "lat": 40.7673, "lon": -73.9712, "routes": ["M1", "M2", "M3", "M4"]},
            {"stop_id": "M1_002", "stop_name": "5 Av & 42 St", "lat": 40.7500, "lon": -73.9800, "routes": ["M1", "M2", "M3", "M4"]},
            {"stop_id": "M1_003", "stop_name": "5 Av & 34 St", "lat": 40.7500, "lon": -73.9850, "routes": ["M1", "M2", "M3", "M4"]},
            {"stop_id": "M1_004", "stop_name": "5 Av & 23 St", "lat": 40.7400, "lon": -73.9900, "routes": ["M1", "M2", "M3", "M4"]},
            {"stop_id": "M1_005", "stop_name": "5 Av & 14 St", "lat": 40.7300, "lon": -73.9950, "routes": ["M1", "M2", "M3", "M4"]},
            
            # Broadway routes
            {"stop_id": "M5_001", "stop_name": "Broadway & 72 St", "lat": 40.7800, "lon": -73.9800, "routes": ["M5", "M7", "M104"]},
            {"stop_id": "M5_002", "stop_name": "Broadway & 57 St", "lat": 40.7700, "lon": -73.9800, "routes": ["M5", "M7", "M104"]},
            {"stop_id": "M5_003", "stop_name": "Broadway & 42 St", "lat": 40.7500, "lon": -73.9850, "routes": ["M5", "M7", "M104"]},
            {"stop_id": "M5_004", "stop_name": "Broadway & 34 St", "lat": 40.7500, "lon": -73.9900, "routes": ["M5", "M7", "M104"]},
            {"stop_id": "M5_005", "stop_name": "Broadway & 23 St", "lat": 40.7400, "lon": -73.9950, "routes": ["M5", "M7", "M104"]},
            
            # Cross-town routes
            {"stop_id": "M14_001", "stop_name": "14 St & 1 Av", "lat": 40.7300, "lon": -73.9800, "routes": ["M14A", "M14D"]},
            {"stop_id": "M14_002", "stop_name": "14 St & 2 Av", "lat": 40.7300, "lon": -73.9850, "routes": ["M14A", "M14D"]},
            {"stop_id": "M14_003", "stop_name": "14 St & 3 Av", "lat": 40.7300, "lon": -73.9900, "routes": ["M14A", "M14D"]},
            {"stop_id": "M14_004", "stop_name": "14 St & 6 Av", "lat": 40.7300, "lon": -73.9950, "routes": ["M14A", "M14D"]},
            {"stop_id": "M14_005", "stop_name": "14 St & 8 Av", "lat": 40.7300, "lon": -74.0000, "routes": ["M14A", "M14D"]},
            
            # East side routes
            {"stop_id": "M15_001", "stop_name": "1 Av & 96 St", "lat": 40.7800, "lon": -73.9500, "routes": ["M15", "M15SBS"]},
            {"stop_id": "M15_002", "stop_name": "1 Av & 86 St", "lat": 40.7700, "lon": -73.9500, "routes": ["M15", "M15SBS"]},
            {"stop_id": "M15_003", "stop_name": "1 Av & 72 St", "lat": 40.7600, "lon": -73.9500, "routes": ["M15", "M15SBS"]},
            {"stop_id": "M15_004", "stop_name": "1 Av & 57 St", "lat": 40.7500, "lon": -73.9500, "routes": ["M15", "M15SBS"]},
            {"stop_id": "M15_005", "stop_name": "1 Av & 42 St", "lat": 40.7400, "lon": -73.9500, "routes": ["M15", "M15SBS"]},
            
            # West side routes
            {"stop_id": "M11_001", "stop_name": "Amsterdam Av & 96 St", "lat": 40.7800, "lon": -73.9700, "routes": ["M11"]},
            {"stop_id": "M11_002", "stop_name": "Amsterdam Av & 86 St", "lat": 40.7700, "lon": -73.9700, "routes": ["M11"]},
            {"stop_id": "M11_003", "stop_name": "Amsterdam Av & 72 St", "lat": 40.7600, "lon": -73.9700, "routes": ["M11"]},
            {"stop_id": "M11_004", "stop_name": "Amsterdam Av & 57 St", "lat": 40.7500, "lon": -73.9700, "routes": ["M11"]},
            {"stop_id": "M11_005", "stop_name": "Amsterdam Av & 42 St", "lat": 40.7400, "lon": -73.9700, "routes": ["M11"]},
            
            # Major transfer points
            {"stop_id": "TRANS_001", "stop_name": "Times Sq-42 St", "lat": 40.7500, "lon": -73.9850, "routes": ["M1", "M2", "M3", "M4", "M5", "M7", "M104"]},
            {"stop_id": "TRANS_002", "stop_name": "Union Sq-14 St", "lat": 40.7300, "lon": -73.9900, "routes": ["M14A", "M14D", "M5", "M7", "M104"]},
            {"stop_id": "TRANS_003", "stop_name": "Central Park-72 St", "lat": 40.7700, "lon": -73.9700, "routes": ["M1", "M2", "M3", "M4", "M5", "M7"]},
        ]
        
        for stop_data in manhattan_stops:
            x, y = self.lat_lon_to_grid(stop_data["lat"], stop_data["lon"])
            
            stop = ManhattanStop(
                stop_id=stop_data["stop_id"],
                stop_name=stop_data["stop_name"],
                lat=stop_data["lat"],
                lon=stop_data["lon"],
                routes=stop_data["routes"],
                x=x,
                y=y,
                wheelchair_boarding=True
            )
            
            self.stops[stop.stop_id] = stop
        
        print(f"✅ Loaded {len(self.stops)} Manhattan bus stops")
        return self.stops
    
    def create_manhattan_routes(self) -> Dict[str, ManhattanRoute]:
        """Create realistic MTA bus routes"""
        print("🚌 Creating Manhattan bus routes...")
        
        # M1-M4 (5th Avenue routes)
        m1_stops = ["M1_001", "M1_002", "M1_003", "M1_004", "M1_005"]
        m2_stops = ["M1_001", "M1_002", "M1_003", "M1_004", "M1_005"]
        m3_stops = ["M1_001", "M1_002", "M1_003", "M1_004", "M1_005"]
        m4_stops = ["M1_001", "M1_002", "M1_003", "M1_004", "M1_005"]
        
        # M5-M7 (Broadway routes)
        m5_stops = ["M5_001", "M5_002", "M5_003", "M5_004", "M5_005"]
        m7_stops = ["M5_001", "M5_002", "M5_003", "M5_004", "M5_005"]
        m104_stops = ["M5_001", "M5_002", "M5_003", "M5_004", "M5_005"]
        
        # M14 (14th Street crosstown)
        m14a_stops = ["M14_001", "M14_002", "M14_003", "M14_004", "M14_005"]
        m14d_stops = ["M14_005", "M14_004", "M14_003", "M14_002", "M14_001"]
        
        # M15 (1st Avenue)
        m15_stops = ["M15_001", "M15_002", "M15_003", "M15_004", "M15_005"]
        m15sbs_stops = ["M15_001", "M15_002", "M15_003", "M15_004", "M15_005"]
        
        # M11 (Amsterdam Avenue)
        m11_stops = ["M11_001", "M11_002", "M11_003", "M11_004", "M11_005"]
        
        routes_data = [
            {"route_id": "M1", "route_name": "M1 Madison Av", "stops": m1_stops, "direction": "SB", "color": "#3b82f6"},
            {"route_id": "M2", "route_name": "M2 Madison Av", "stops": m2_stops, "direction": "SB", "color": "#10b981"},
            {"route_id": "M3", "route_name": "M3 Madison Av", "stops": m3_stops, "direction": "SB", "color": "#f59e0b"},
            {"route_id": "M4", "route_name": "M4 Madison Av", "stops": m4_stops, "direction": "SB", "color": "#ef4444"},
            {"route_id": "M5", "route_name": "M5 Broadway", "stops": m5_stops, "direction": "SB", "color": "#8b5cf6"},
            {"route_id": "M7", "route_name": "M7 Broadway", "stops": m7_stops, "direction": "SB", "color": "#06b6d4"},
            {"route_id": "M104", "route_name": "M104 Broadway", "stops": m104_stops, "direction": "SB", "color": "#84cc16"},
            {"route_id": "M14A", "route_name": "M14A 14 St", "stops": m14a_stops, "direction": "EB", "color": "#f97316"},
            {"route_id": "M14D", "route_name": "M14D 14 St", "stops": m14d_stops, "direction": "WB", "color": "#ec4899"},
            {"route_id": "M15", "route_name": "M15 1 Av", "stops": m15_stops, "direction": "SB", "color": "#6366f1"},
            {"route_id": "M15SBS", "route_name": "M15 SBS 1 Av", "stops": m15sbs_stops, "direction": "SB", "color": "#14b8a6"},
            {"route_id": "M11", "route_name": "M11 Amsterdam Av", "stops": m11_stops, "direction": "SB", "color": "#a855f7"},
        ]
        
        for route_data in routes_data:
            route = ManhattanRoute(
                route_id=route_data["route_id"],
                route_name=route_data["route_name"],
                stops=route_data["stops"],
                direction=route_data["direction"],
                color=route_data["color"]
            )
            self.routes[route.route_id] = route
        
        print(f"✅ Created {len(self.routes)} Manhattan bus routes")
        return self.routes
    
    def get_manhattan_demand_patterns(self) -> Dict[str, float]:
        """Get realistic demand patterns for Manhattan"""
        return {
            # Peak hours (7-9 AM, 5-7 PM)
            "morning_rush": 1.5,
            "evening_rush": 1.3,
            # Off-peak
            "midday": 0.8,
            "night": 0.3,
            # Weekend patterns
            "weekend": 0.6
        }
    
    def get_route_colors(self) -> Dict[str, str]:
        """Get route colors for visualization"""
        return {route_id: route.color for route_id, route in self.routes.items()}
    
    def export_manhattan_data(self, output_file: str = "manhattan_bus_data.json"):
        """Export processed Manhattan data"""
        data = {
            "stops": {
                stop_id: {
                    "stop_id": stop.stop_id,
                    "stop_name": stop.stop_name,
                    "lat": stop.lat,
                    "lon": stop.lon,
                    "x": stop.x,
                    "y": stop.y,
                    "routes": stop.routes,
                    "wheelchair_boarding": stop.wheelchair_boarding
                }
                for stop_id, stop in self.stops.items()
            },
            "routes": {
                route_id: {
                    "route_id": route.route_id,
                    "route_name": route.route_name,
                    "stops": route.stops,
                    "direction": route.direction,
                    "color": route.color
                }
                for route_id, route in self.routes.items()
            },
            "grid_size": (self.grid_width, self.grid_height),
            "bounds": {
                "min_lat": self.min_lat,
                "max_lat": self.max_lat,
                "min_lon": self.min_lon,
                "max_lon": self.max_lon
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Exported Manhattan data to {output_file}")
        return data

def main():
    """Main function to process Manhattan data"""
    print("🗽 PROCESSING MANHATTAN BUS DATA")
    print("=" * 50)
    
    parser = ManhattanDataParser()
    
    # Load stops and routes
    stops = parser.load_manhattan_stops()
    routes = parser.create_manhattan_routes()
    
    # Export data
    data = parser.export_manhattan_data()
    
    print(f"\n📊 MANHATTAN SYSTEM SUMMARY:")
    print(f"  Stops: {len(stops)}")
    print(f"  Routes: {len(routes)}")
    print(f"  Grid: {parser.grid_width}x{parser.grid_height}")
    print(f"  Coverage: Manhattan (40.7°N to 40.8°N, 74.0°W to 73.9°W)")
    
    print(f"\n🚌 MAJOR ROUTES:")
    for route_id, route in routes.items():
        print(f"  {route_id}: {route.route_name} ({len(route.stops)} stops)")
    
    print(f"\n📍 KEY STOPS:")
    key_stops = ["TRANS_001", "TRANS_002", "TRANS_003"]
    for stop_id in key_stops:
        if stop_id in stops:
            stop = stops[stop_id]
            print(f"  {stop.stop_name}: {', '.join(stop.routes)}")
    
    return parser

if __name__ == "__main__":
    parser = main()
