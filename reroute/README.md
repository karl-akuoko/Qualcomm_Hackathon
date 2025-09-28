# Manhattan Bus Dispatch System - Web & Android

## 🚀 Quick Start

### 🌐 **Web Version**
```bash
cd /Users/ehsan/Downloads/IdeaProjects/Qualcomm/Qualcomm_Hackathon/reroute
python start_comparison.py
```
Then visit: **http://localhost:8000**

### 📱 **Android Version**
1. Open Android Studio
2. Open project: `/Users/ehsan/Downloads/IdeaProjects/Qualcomm/Qualcomm_Hackathon/reroute/android`
3. Run the app (no API key required!)

**See [ANDROID_SETUP_NO_API_KEY.md](ANDROID_SETUP_NO_API_KEY.md) for easy setup (no API key required)**
**Or [ANDROID_SETUP.md](ANDROID_SETUP.md) for Google Maps version**

A reinforcement learning-driven bus dispatch system that demonstrates adaptive routing capabilities on a Snapdragon X Elite laptop. This MVP proves that RL can reduce rider wait times and overcrowding compared to fixed schedules, even under judge-triggered disruptions.

## 🎯 MVP Goals

- **Prove RL effectiveness**: ≥20% reduction in average wait times vs baseline
- **Reduce overcrowding**: ≥30% improvement in load distribution
- **Demonstrate resilience**: Recovery within 120 seconds after disruptions
- **Maintain stability**: ≤1 replan per bus every 45 seconds
- **Run on-device**: Full system runs on Snapdragon X Elite hardware

## 🏗️ Architecture

### Core Components

- **Environment** (`env/`): Manhattan-style 20×20 grid simulation
- **RL Training** (`rl/`): PPO policy training and ONNX export
- **Server** (`server/`): FastAPI backend with WebSocket live updates
- **Clients** (`clients/`): React dashboard and React Native mobile app

### Key Features

- **Grid Simulation**: 32 strategic stops, 6-8 buses, time-of-day demand patterns
- **RL Policy**: PPO with discrete actions (continue, high-demand, skip-low, hold)
- **Real-time Updates**: WebSocket streaming at 5-10 Hz
- **Stress Testing**: Road closures, traffic jams, demand surges
- **Baseline Comparison**: Side-by-side static vs RL performance

## 🗽 Cross-Platform Features

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

### ✅ **Cross-Platform Support**
- **🌐 Web Version** - Browser-based with MapLibre GL JS
- **📱 Android Version** - Native Android app with Google Maps
- **🔄 Same Backend** - Both versions use the same Python server
- **📊 Identical Features** - All functionality available on both platforms

## 🚀 Quick Start

### 1. Setup

```bash
# Install dependencies and train model
python setup.py

# Quick setup (minimal training)
python setup.py --quick
```

### 2. Start Server

```bash
# Start FastAPI server
./start_server.sh

# Or manually
cd server && python fastapi_server.py
```

### 3. View Dashboard

Open http://localhost:8000 in your browser to see:
- Side-by-side maps (Static vs RL)
- Real-time KPI charts
- Stress test controls
- Performance improvements

### 4. Run Demo

```bash
# Run predefined demo scenarios
./run_demo.sh

# Or manually
cd scripts && python demo_seed.py --scenario morning_rush --mode rl
```

## 📱 Mobile App

The React Native mobile app provides:
- Live bus tracking
- Stop ETAs with RL savings badges
- Nearby bus locations
- Real-time performance metrics

## 🎮 Demo Scenarios

### Morning Rush Hour
- High demand during 8-9 AM
- Traffic congestion in business district
- Road closure at central intersection
- **Expected**: 15-35% wait time improvement

### Event Surge
- Stadium event with 4x demand multiplier
- Multiple traffic jams
- **Expected**: 25-45% overcrowding reduction

### Infrastructure Failure
- Multiple road closures
- Severe traffic disruptions
- **Expected**: 60-90% resilience score

## 🔧 API Endpoints

### Control
- `POST /mode` - Switch between static/RL modes
- `POST /stress` - Apply disruptions (closure, traffic, surge)
- `POST /reset` - Reset simulation with seed

### Monitoring
- `GET /status` - System status and mode
- `GET /state` - Current system state snapshot
- `GET /metrics` - Detailed performance metrics
- `WS /live` - Real-time WebSocket updates

### Example Usage

```bash
# Switch to RL mode
curl -X POST http://localhost:8000/mode -H "Content-Type: application/json" -d '{"mode": "rl"}'

# Apply road closure
curl -X POST http://localhost:8000/stress -H "Content-Type: application/json" -d '{"type": "closure", "params": {"stop_id": 210}}'

# Get current metrics
curl http://localhost:8000/metrics
```

## 🧠 RL Training

### Training the Model

```bash
# Full training (100k timesteps)
cd rl && python train.py --mode train --timesteps 100000

# Quick training (10k timesteps)
cd rl && python train.py --mode train --timesteps 10000
```

### Export to ONNX

```bash
# Export trained model
cd rl && python export_onnx.py --input ppo_bus_final --output ppo_bus_policy.onnx
```

### Evaluation

```bash
# Evaluate trained policy
cd rl && python eval.py --model ppo_bus_final --episodes 10
```

## 📊 Performance Metrics

### Success Criteria

- **Wait Time**: ≥20% reduction vs baseline
- **Overcrowding**: ≥30% improvement in load distribution
- **Resilience**: Recovery within 120 seconds after disruptions
- **Stability**: ≤1 replan per bus every 45 seconds
- **On-device**: Smooth 60 FPS UI updates

### KPI Tracking

- Average wait time (minutes)
- 90th percentile wait time
- Load standard deviation (overcrowding)
- Total distance traveled
- Replan frequency

## 🛠️ Development

### Project Structure

```
reroute/
├── start_comparison.py              # 🚀 Main startup script
├── server/
│   └── fastapi_manhattan_comparison.py  # 🗽 Enhanced server with all features
├── env/                            # 🏗️ Environment components
│   ├── city.py                     # Manhattan grid and stops
│   ├── bus.py                      # Bus fleet management
│   ├── riders.py                   # Rider generation
│   ├── traffic.py                  # Traffic modeling
│   ├── reward.py                   # Reward calculation
│   └── wrappers.py                 # Gym environment
├── rl/                             # 🤖 Reinforcement learning
│   ├── train.py                    # PPO training
│   ├── eval.py                     # Policy evaluation
│   ├── export_onnx.py              # ONNX export
│   └── policies.py                 # Custom policies
├── ui_data/                        # 📊 UI and data files
│   ├── gtfs_m/                     # MTA GTFS data
│   └── sample_manhattan_stops.geojson
├── clients/                        # 📱 Frontend clients
│   ├── dashboard/                  # React web dashboard
│   └── mobile/                     # React Native app
├── android/                        # 📱 Android app
│   ├── app/
│   │   ├── build.gradle            # Android dependencies
│   │   └── src/main/
│   │       ├── AndroidManifest.xml # App permissions
│   │       ├── java/com/qualcomm/reroute/
│   │       │   ├── MainActivity.kt # Main activity
│   │       │   ├── data/           # Data models & API
│   │       │   ├── ui/             # UI screens & components
│   │       │   └── di/             # Dependency injection
│   │       └── res/                # Android resources
│   ├── build.gradle                # Project build config
│   └── settings.gradle             # Project settings
├── README_CLEAN.md                 # 📖 Clean documentation
└── ANDROID_SETUP.md               # 📱 Android setup guide
```

### Running Both Versions

#### 🌐 **Web Version**
```bash
# Start the Python server
python start_comparison.py

# Open browser
open http://localhost:8000
```

#### 📱 **Android Version**
```bash
# 1. Start the Python server (same as web version)
python start_comparison.py

# 2. Open Android Studio
# 3. Open project: reroute/android
# 4. Configure Google Maps API key
# 5. Run the app
```

**Both versions connect to the same Python server and provide identical functionality!**

### Adding New Features

1. **New Disruptions**: Add to `env/wrappers.py` `apply_disruption()`
2. **New Metrics**: Extend `env/reward.py` and `server/state_store.py`
3. **New Policies**: Implement in `rl/policies.py`
4. **New Scenarios**: Add to `scripts/demo_seed.py`
5. **Android UI**: Add new components in `android/app/src/main/java/com/qualcomm/reroute/ui/`

## 🐛 Troubleshooting

### Common Issues

1. **ONNX model not found**
   ```bash
   cd rl && python export_onnx.py --input ppo_bus_final --output ppo_bus_policy.onnx
   ```

2. **WebSocket connection failed**
   - Check server is running on port 8000
   - Verify firewall settings
   - Try `ws://localhost:8000/live`

3. **Training too slow**
   - Use `--quick` flag for faster setup
   - Reduce timesteps: `--timesteps 10000`
   - Use GPU if available

4. **Memory issues**
   - Reduce grid size in `env/wrappers.py`
   - Decrease number of buses
   - Lower max episode time

### Performance Optimization

- **Simulation Speed**: Adjust `time_step` in environment
- **Update Frequency**: Modify WebSocket broadcast rate
- **Model Size**: Use smaller neural network architecture
- **Batch Processing**: Process multiple environments in parallel

## 📈 Demo Script

### 5-Minute Demo Flow

1. **Start Static** (0-90s): Show baseline performance during morning rush
2. **Switch to RL** (90-180s): Watch KPIs improve as buses adapt
3. **Road Closure** (180-300s): Apply disruption, see RL detour vs static stall
4. **Demand Surge** (300-420s): Stadium event, RL steers capacity efficiently
5. **Final Comparison** (420-420s): Show cumulative improvements

### Key Talking Points

- **Real-time Adaptation**: RL responds to disruptions within seconds
- **Measurable Improvements**: Concrete percentage improvements
- **On-device Performance**: Full system runs on Snapdragon hardware
- **Scalability**: Architecture supports larger cities and more buses

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Stable Baselines3 for RL algorithms
- FastAPI for web framework
- React/React Native for frontend
- Qualcomm for Snapdragon X Elite hardware
