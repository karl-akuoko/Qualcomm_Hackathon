# 🚌 RL-Driven Bus Routing System

A reinforcement learning system that optimizes bus routing in real-time to reduce rider wait times and improve service resilience. Built for demonstration on Snapdragon X Elite hardware.

## 🎯 MVP Goals

**Primary Objective**: Prove that an RL-driven dispatcher can lower rider wait times and reduce overcrowding versus a fixed schedule in a synthetic city, running live on Snapdragon X Elite.

**Success Criteria**:
- ΔAvg wait: RL ≥20% lower than baseline
- Overcrowding: ≥30% reduction vs baseline  
- Resilience: Recovery within 120s after disruptions
- Performance: Runs entirely on Snapdragon X Elite

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │  FastAPI Server  │    │  Mobile App     │
│   (React)       │◄──►│  + WebSocket     │◄──►│  (React Native) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Gym Environment │
                    │  + ONNX Runtime  │
                    └──────────────────┘
```

### Core Components

- **Environment**: 20×20 grid city with 35 stops and 6 buses
- **RL Agent**: PPO policy trained with Stable Baselines3
- **Inference**: ONNX Runtime for on-device execution
- **Server**: FastAPI with WebSocket live feed
- **Dashboard**: React app with dual map visualization
- **Mobile**: React Native rider experience

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Snapdragon X Elite laptop (or compatible hardware)

### Installation

1. **Clone and setup Python environment**:
```bash
cd reroute
pip install -r requirements.txt
```

2. **Train the RL model**:
```bash
python -m rl.train
```

3. **Export to ONNX**:
```bash
python -m rl.export_onnx
```

4. **Start the server**:
```bash
python -m server.api
```

5. **Setup dashboard**:
```bash
cd clients/dashboard
npm install
npm run dev
```

6. **Setup mobile app**:
```bash
cd clients/mobile
npm install
npx react-native run-android  # or run-ios
```

### Demo Execution

Run the automated demo script:
```bash
python scripts/demo_seed.py
```

Or follow the manual demo script in `docs/demo_script.md`.

## 📊 Performance Metrics

### Target Performance
- **Wait Time Improvement**: ≥20% reduction
- **Overcrowding Reduction**: ≥30% improvement
- **Resilience**: <120s recovery from disruptions
- **Smoothness**: <1 replan per 45s
- **Inference Latency**: <10ms on Snapdragon X Elite

### Real-time Monitoring
- Live KPI tracking (avg wait, P90 wait, load std dev)
- Bus position and capacity monitoring
- Disruption detection and response
- Rider experience metrics

## 🎮 Demo Scenarios

### 1. Baseline vs RL Comparison
- Start with fixed schedule showing rising wait times
- Switch to RL policy and observe immediate improvement
- Highlight KPI deltas in real-time

### 2. Resilience Testing
- Trigger road closures and observe adaptive routing
- Test demand surges and capacity reallocation
- Measure recovery time and service maintenance

### 3. Mobile Experience
- Show live bus tracking and ETA predictions
- Display "RL savings" badges for riders
- Demonstrate real-time service improvements

## 🔧 Technical Details

### Environment Design
- **Grid**: 20×20 Manhattan-like layout
- **Stops**: 35 distributed stops with time-of-day demand
- **Buses**: 6 buses with 50-passenger capacity
- **Actions**: {continue, go_to_high_demand, skip_low_demand, short_hold}

### Reward Function
```python
reward = -avg_wait - 2×overcrowd - 0.1×extra_distance - 0.05×replan
```

### ONNX Optimization
- Model size: <100MB
- Inference time: <10ms
- Memory usage: <100MB
- Compatible with Snapdragon X Elite NPU

### API Endpoints
- `POST /mode` - Switch between static/RL modes
- `POST /stress` - Trigger disruption scenarios
- `POST /reset` - Reset simulation with new seed
- `WS /live` - Real-time simulation data feed

## 📱 User Interfaces

### Web Dashboard
- Dual map visualization (static vs RL)
- Real-time KPI charts and metrics
- Stress test controls
- Performance comparison tools

### Mobile App
- Live bus tracking and ETAs
- Stop information and queue lengths
- RL savings notifications
- Issue reporting capabilities

## 🧪 Testing and Validation

### Automated Testing
```bash
# Run evaluation suite
python -m rl.eval

# Benchmark ONNX performance
python -m rl.export_onnx --benchmark

# Test API endpoints
pytest tests/
```

### Demo Validation
- Automated demo script with success criteria
- Performance benchmarking on target hardware
- Stress testing with various disruption scenarios
- Mobile app functionality testing

## 🔮 Future Enhancements

### Short-term (v0.1)
- Headway regularization to prevent bunching
- Deterministic demo seeds for reproducibility
- Enhanced KPI visualization

### Long-term (v1.0)
- Multi-agent coordination policies
- Real GTFS data integration
- Predictive demand modeling
- Emissions and sustainability metrics

## 📚 Documentation

- [Demo Script](docs/demo_script.md) - Complete demo walkthrough
- [API Reference](docs/api.md) - Server endpoints and WebSocket protocol
- [Architecture Guide](docs/architecture.md) - System design and components
- [Development Guide](docs/development.md) - Contributing and extending

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Stable Baselines3 for RL algorithms
- FastAPI for web server framework
- React/React Native for frontend development
- ONNX Runtime for model deployment
- Snapdragon X Elite for target hardware platform

---

**Built for Qualcomm Hackathon 2024** | **Optimized for Snapdragon X Elite**