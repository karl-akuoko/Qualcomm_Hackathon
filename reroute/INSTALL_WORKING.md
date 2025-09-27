# Bus Dispatch RL - Working Installation

## The Problem
The code uses `gym` but should use `gymnasium` (the newer version). This causes import errors.

## The Solution

### Step 1: Install the RIGHT packages
```bash
pip install gymnasium  # NOT gym
pip install numpy networkx matplotlib fastapi uvicorn websockets pydantic stable-baselines3 torch pandas
```

### Step 2: Run the working startup
```bash
python start_working.py
```

This script will:
1. Install all required packages
2. Test the environment
3. Run a demo
4. Show you it's working

## Alternative: Manual Fix

If you want to fix it manually:

### 1. Install gymnasium (not gym)
```bash
pip install gymnasium
```

### 2. The import is already fixed in wrappers.py
The file now uses:
```python
import gymnasium as gym
from gymnasium import spaces
```

### 3. Test it works
```bash
python test_basic.py
```

## What Was Wrong

- Code was importing `gym` but should import `gymnasium`
- `gym` is the old version, `gymnasium` is the new version
- `gymnasium` is backward compatible but has a different import name

## Expected Output

After running `python start_working.py`, you should see:
```
✓ numpy
✓ gymnasium  
✓ networkx
✓ BusDispatchEnv
✓ Environment creation
✓ Environment reset (obs shape: ...)
✓ Environment step (reward: ...)
Running simulation...
Step 0: Reward = ..., Total = ...
...
✓ Everything is working!
```

## If It Still Doesn't Work

1. Make sure you're in the `reroute` directory
2. Check that `env/wrappers.py` exists
3. Try: `export PYTHONPATH=$PYTHONPATH:$(pwd)`
4. Then run: `python start_working.py`
