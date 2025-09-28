# Manhattan Bus Dispatch System - Clean Version

## 🚀 Quick Start

```bash
cd /Users/ehsan/Downloads/IdeaProjects/Qualcomm/Qualcomm_Hackathon/reroute
python start_comparison.py
```

Then visit: **http://localhost:8000**

## 🗽 Features

### ✅ **Perfect Grid Alignment**
- **45° map tilt** for roads perfectly parallel/perpendicular to screen
- **Streets run up/down**, **avenues run left/right** aligned with screen
- **All 335+ Manhattan bus stops** from GTFS data + UI data files

### ✅ **Road Disruption System**
- 🚧 **Road Closures** - Complete blockage (0% movement)
- 🚗💥 **Car Crashes** - Severe slowdown (30% movement)  
- 🧊 **Icy Roads** - Moderate slowdown (60% movement)
- 🚦 **Traffic Jams** - Light slowdown (70% movement)
- 🧹 **Clear All** - Remove all disruptions

### ✅ **Real-time Performance Comparison**
- **Baseline Routes** (red circles) - Untrained buses
- **Optimized Routes** (green circles) - Trained buses
- **Live Metrics** - Wait times, passenger counts, efficiency
- **Disruption Impact** - See how road conditions affect performance

## 📁 Project Structure

```
reroute/
├── start_comparison.py              # Main startup script
├── server/
│   └── fastapi_manhattan_comparison.py  # Main server with all features
├── env/                            # Environment components
│   ├── bus.py                      # Bus fleet management
│   ├── city.py                     # Manhattan grid system
│   ├── riders.py                   # Passenger generation
│   ├── reward.py                   # Performance metrics
│   └── wrappers.py                 # Gymnasium environment
├── rl/                             # Reinforcement learning
│   ├── train.py                    # Training scripts
│   ├── policies.py                 # RL policies
│   └── export_onnx.py              # Model export
├── ui_data/                        # UI and data files
│   ├── gtfs_m/                     # MTA GTFS data
│   ├── sample_manhattan_stops.geojson
│   └── build_manhattan_bus_stops.py
└── clients/                        # Frontend clients
    ├── dashboard/                   # React dashboard
    └── mobile/                      # Mobile app
```

## 🎯 Key Components

### **Enhanced Manhattan System**
- **Perfect Grid Alignment**: Roads perfectly aligned with screen
- **All Bus Stops**: Every stop from GTFS + UI data files
- **Road Disruptions**: Real-time road condition simulation
- **Performance Comparison**: Baseline vs optimized routes

### **Real-time Controls**
- **Add Disruptions**: Click buttons to add road closures, crashes, etc.
- **Clear All**: Remove all disruptions instantly
- **Live Metrics**: See immediate impact on wait times
- **Bus Movement**: Watch buses adapt to road conditions

## 🚌 How It Works

1. **Load All Data**: GTFS stops + UI data files (335+ stops total)
2. **Perfect Grid**: 45° tilt makes roads perfectly aligned with screen
3. **Baseline vs Optimized**: Compare untrained vs trained bus routes
4. **Add Disruptions**: Use buttons to simulate real-world road conditions
5. **Live Performance**: See how disruptions affect wait times and efficiency

## 🎮 Usage

1. **Start System**: `python start_comparison.py`
2. **Open Browser**: Visit `http://localhost:8000`
3. **Add Disruptions**: Click road disruption buttons
4. **Watch Performance**: See real-time impact on wait times
5. **Clear Disruptions**: Remove all road conditions

## 📊 Performance Metrics

- **Average Wait Time**: Real-time passenger wait times
- **Total Passengers**: Current system load
- **Bus Count**: Active buses in system
- **Stop Count**: Total bus stops loaded
- **Disruption Impact**: How road conditions affect performance

## 🗽 Manhattan Features

- **Real GTFS Data**: All 335+ Manhattan bus stops
- **Perfect Grid**: Streets/avenues aligned with screen
- **Road Disruptions**: Simulate real-world conditions
- **Performance Comparison**: Baseline vs optimized routes
- **Live Updates**: Real-time system monitoring

---

**Ready to run!** Just execute `python start_comparison.py` and visit `http://localhost:8000` 🚀
