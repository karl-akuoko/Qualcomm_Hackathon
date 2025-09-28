#!/usr/bin/env python3
"""
Start server with proper RL training and passenger boarding
"""

import os
import sys
import subprocess
import time
import signal

def kill_port_8000():
    """Kill any processes using port 8000"""
    try:
        result = subprocess.run(['lsof', '-ti', ':8000'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    print(f"✓ Killing process {pid} on port 8000")
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        time.sleep(1)
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    except (ProcessLookupError, ValueError):
                        pass
            print("✓ Port 8000 cleared")
        else:
            print("✓ Port 8000 is already free")
            
    except FileNotFoundError:
        print("⚠ Cannot check port 8000 status")
    except Exception as e:
        print(f"⚠ Error checking port 8000: {e}")

def train_simple_model():
    """Train a simple RL model for bus dispatching"""
    print("🤖 Training simple RL model...")
    
    try:
        # Create a simple training script
        training_script = """
import os
import sys
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def create_env():
    return BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=60.0,
        seed=42
    )

# Create environment
env = make_vec_env(create_env, n_envs=1)

# Create simple PPO model
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=512,
    batch_size=64,
    n_epochs=5,
    gamma=0.99,
    verbose=1,
    device="cpu"
)

print("Training for 10000 steps...")
model.learn(total_timesteps=10000, progress_bar=True)

# Save model
model.save("simple_bus_model")
print("✓ Model saved as simple_bus_model")

# Test the model
obs = env.reset()
for i in range(10):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, info = env.step(action)
    if done:
        obs = env.reset()
    print(f"Step {i}: Reward = {reward[0]:.2f}")

print("✓ Training completed!")
"""
        
        # Write training script
        with open('quick_train.py', 'w') as f:
            f.write(training_script)
        
        # Run training
        result = subprocess.run([sys.executable, 'quick_train.py'], 
                              capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✓ RL model trained successfully!")
            return True
        else:
            print(f"✗ Training failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Training error: {e}")
        return False

def main():
    """Start server with training"""
    print("=" * 60)
    print("STARTING SERVER WITH RL TRAINING")
    print("=" * 60)
    
    # Check directory
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    # Kill any existing servers
    print("🔧 Killing existing servers...")
    kill_port_8000()
    time.sleep(2)
    
    # Train RL model
    print("🤖 Training RL model...")
    if not train_simple_model():
        print("⚠ Training failed, continuing with static mode")
    
    print("✓ Starting fixed server with passenger boarding")
    print("✓ Server: http://localhost:8000")
    print("✓ Manhattan grid with moving buses and passengers")
    print("✓ Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Change to server directory and start fixed server
        os.chdir('server')
        subprocess.run([sys.executable, 'fastapi_fixed.py'])
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
    except Exception as e:
        print(f"✗ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
