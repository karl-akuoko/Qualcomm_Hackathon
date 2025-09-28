# 🗽 Manhattan Bus Dispatch System

## Overview

A realistic bus dispatch simulation system using **actual Manhattan MTA data** with real bus stops, routes, and demand patterns. This system demonstrates RL-driven bus dispatch optimization against a static baseline using real-world Manhattan geography and transit infrastructure.

## 🚌 Real MTA Data Integration

### Bus Routes
- **M1, M2, M3, M4**: Madison Avenue routes (5th Avenue corridor)
- **M5, M7, M104**: Broadway routes (major north-south corridor)
- **M14A, M14D**: 14th Street crosstown routes
- **M15, M15SBS**: 1st Avenue routes (east side)
- **M11**: Amsterdam Avenue route (west side)

### Key Bus Stops
- **Times Square-42 St**: Major transfer point (M1, M2, M3, M4, M5, M7, M104)
- **Union Square-14 St**: Major transfer point (M14A, M14D, M5, M7, M104)
- **Central Park-72 St**: Major transfer point (M1, M2, M3, M4, M5, M7)
- **5th Avenue stops**: High-demand corridor
- **Broadway stops**: Major north-south route
- **14th Street stops**: Crosstown connections

## 🎯 Realistic Demand Patterns

### Time-Based Demand
- **Morning Rush (7-9 AM)**: 1.5x base demand
- **Evening Rush (5-7 PM)**: 1.3x base demand
- **Midday (10 AM-4 PM)**: 0.8x base demand
- **Night (10 PM-6 AM)**: 0.3x base demand

### Location-Based Demand
- **Major Transfer Points**: 2.5x base demand
- **5th Avenue Corridor**: 1.8x base demand
- **Broadway Corridor**: 1.6x base demand
- **14th Street Crosstown**: 1.4x base demand

## 🗺️ Manhattan Geography

### Grid System
- **100x100 grid** representing Manhattan
- **Latitude**: 40.7°N to 40.8°N
- **Longitude**: 74.0°W to 73.9°W
- **Real coordinate mapping** from lat/lon to grid positions

### Street Layout
- **North-South Avenues**: 5th Ave, Broadway, 1st Ave, Amsterdam Ave
- **East-West Streets**: 14th St, 23rd St, 34th St, 42nd St, 57th St, 72nd St
- **Major Intersections**: Times Square, Union Square, Central Park

## 🚌 Bus Fleet

### Fleet Composition
- **28 buses** across 12 routes
- **2-3 buses per route** (more for major routes)
- **40-passenger capacity** per bus
- **Real route colors** matching MTA branding

### Route Characteristics
- **M1-M4**: Madison Avenue (blue theme)
- **M5, M7, M104**: Broadway (purple theme)
- **M14A, M14D**: 14th Street (orange theme)
- **M15, M15SBS**: 1st Avenue (teal theme)
- **M11**: Amsterdam Avenue (purple theme)

## 📊 Performance Metrics

### Key Performance Indicators (KPIs)
- **Average Wait Time**: Target < 5 minutes
- **Total Passengers**: Real-time passenger count
- **System Efficiency**: 0-100% efficiency score
- **Load Balance**: Standard deviation of bus loads

### Realistic Targets
- **Peak Hour Wait Time**: < 3 minutes
- **Off-Peak Wait Time**: < 2 minutes
- **Load Balance**: < 10 passengers standard deviation
- **System Efficiency**: > 80%

## 🎮 Interactive Features

### Mode Switching
- **Static Mode**: Fixed schedule baseline
- **RL Mode**: AI-optimized dispatch
- **Real-time comparison** of performance

### Stress Testing
- **Road Closure**: Simulate construction/accidents
- **Traffic Jam**: Increased travel times
- **Demand Surge**: Event-driven passenger spikes

### Live Visualization
- **Real-time bus tracking**
- **Passenger queue visualization**
- **Route performance charts**
- **KPI dashboard**

## 🚀 Getting Started

### Quick Start
```bash
cd /Users/ehsan/Downloads/IdeaProjects/Qualcomm/Qualcomm_Hackathon/reroute
python start_manhattan.py
```

### Access the System
- **Web Dashboard**: http://localhost:8000
- **Real-time Updates**: WebSocket connection
- **Mobile Optimized**: Responsive design

## 📱 Mobile Features

### Android App Compatibility
- **Responsive design** for mobile screens
- **Touch-friendly controls**
- **Optimized performance** for mobile devices
- **Real-time updates** via WebSocket

### Key Mobile Features
- **Manhattan map visualization**
- **Bus tracking** with real-time positions
- **Stop information** with wait times
- **Route planning** assistance

## 🔧 Technical Architecture

### Backend Components
- **FastAPI Server**: REST API and WebSocket
- **Manhattan Data Parser**: Real MTA data processing
- **Bus Dispatch System**: Simulation engine
- **RL Integration**: AI optimization

### Frontend Components
- **React Dashboard**: Real-time visualization
- **Manhattan Map**: SVG-based street grid
- **Performance Charts**: Recharts integration
- **Mobile UI**: Touch-optimized interface

### Data Flow
1. **Real MTA Data** → Data Parser
2. **Parsed Data** → Bus Dispatch System
3. **Simulation State** → FastAPI Server
4. **Live Updates** → WebSocket → Frontend
5. **User Interactions** → API → System Updates

## 📈 Scaling Capabilities

### Current System
- **28 stops** across Manhattan
- **12 bus routes** (M1-M15SBS)
- **28 buses** in operation
- **Real-time simulation** at 10 Hz

### Scaling Potential
- **100+ stops**: Full Manhattan coverage
- **50+ routes**: Complete MTA network
- **200+ buses**: Realistic fleet size
- **City-wide**: All 5 boroughs

### Performance Characteristics
- **Linear scaling** with system size
- **Real-time updates** maintained
- **Mobile performance** optimized
- **Memory efficient** data structures

## 🎯 Demo Scenarios

### Scenario 1: Morning Rush Hour
- **Time**: 8:00 AM
- **Demand**: 1.5x base
- **Challenge**: High passenger volume
- **RL Solution**: Dynamic routing to high-demand stops

### Scenario 2: Evening Rush Hour
- **Time**: 6:00 PM
- **Demand**: 1.3x base
- **Challenge**: Commuter exodus
- **RL Solution**: Load balancing across routes

### Scenario 3: Weekend Service
- **Time**: Saturday 2:00 PM
- **Demand**: 0.6x base
- **Challenge**: Reduced service efficiency
- **RL Solution**: Optimized route coverage

### Scenario 4: Event Surge
- **Time**: Friday 7:00 PM
- **Demand**: 2.0x base (concert/sports)
- **Challenge**: Sudden passenger spike
- **RL Solution**: Rapid response to demand changes

## 🏆 Success Metrics

### MVP Success Criteria
- **20% reduction** in average wait time vs static
- **30% reduction** in overcrowding vs static
- **120-second recovery** from disruptions
- **Smooth operation** on Snapdragon X Elite

### Real-World Impact
- **Realistic simulation** of Manhattan transit
- **Actionable insights** for MTA operations
- **Scalable architecture** for city-wide deployment
- **Mobile-ready** for passenger apps

## 🔮 Future Enhancements

### Phase 2 Features
- **Real GTFS data** integration
- **Weather impact** modeling
- **Multi-modal** connections (subway, bus)
- **Predictive analytics** for demand

### Phase 3 Features
- **City-wide coverage** (all 5 boroughs)
- **Real-time MTA data** integration
- **Passenger app** development
- **MTA partnership** for real deployment

## 📚 Documentation

### System Files
- `manhattan_data_parser.py`: MTA data processing
- `server/fastapi_manhattan.py`: Main server
- `start_manhattan.py`: Startup script
- `UI_data/`: Real MTA data files

### Key Features
- **Real Manhattan stops** and routes
- **Realistic demand patterns**
- **Mobile-optimized UI**
- **RL vs Static comparison**
- **Stress testing capabilities**

---

**🗽 Manhattan Bus Dispatch System** - Bringing AI to NYC Transit
