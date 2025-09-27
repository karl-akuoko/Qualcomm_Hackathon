# Bus Dispatch RL - Simple Startup

## Quick Start (3 steps)

### 1. Install Dependencies
```bash
python install_simple.py
```

### 2. Run Demo (No Server Needed)
```bash
python run_demo_simple.py
```

### 3. Run with Server (For Dashboard)
```bash
python start_simple.py
```
Then open http://localhost:8000

## What Each Script Does

- **`install_simple.py`** - Installs required Python packages
- **`run_demo_simple.py`** - Runs simulation without server (just shows results)
- **`start_simple.py`** - Starts the web server for dashboard

## Troubleshooting

### If packages fail to install:
```bash
pip install numpy fastapi uvicorn stable-baselines3 torch gymnasium networkx
```

### If you get import errors:
Make sure you're in the `reroute` directory and run:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### If server won't start:
Check if port 8000 is free:
```bash
lsof -i :8000
```

## Expected Output

The demo should show:
- Environment creation
- Simulation running with time/performance updates
- Final results with improvement percentages
- MVP success criteria check

## Files You Need

- `env/wrappers.py` - Main environment
- `env/city.py` - Grid simulation  
- `env/bus.py` - Bus management
- `env/riders.py` - Rider generation
- `env/traffic.py` - Traffic modeling
- `env/reward.py` - Reward calculation
- `server/fastapi_server.py` - Web server

That's it! No complex setup, just run the scripts.
