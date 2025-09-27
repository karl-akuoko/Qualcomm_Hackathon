#!/usr/bin/env python3
"""
Setup script for Bus Dispatch RL MVP
Installs dependencies, trains model, and prepares system for demo
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return None

def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    
    requirements_file = Path("data/requirements.txt")
    if not requirements_file.exists():
        print("✗ requirements.txt not found")
        return False
    
    result = run_command(f"pip install -r {requirements_file}", "Installing dependencies")
    return result is not None

def train_rl_model():
    """Train the RL model"""
    print("Training RL model...")
    
    # Check if training script exists
    train_script = Path("rl/train.py")
    if not train_script.exists():
        print("✗ Training script not found")
        return False
    
    # Run training
    result = run_command("cd rl && python train.py --mode train --timesteps 50000", "Training RL model")
    return result is not None

def export_onnx_model():
    """Export trained model to ONNX"""
    print("Exporting model to ONNX...")
    
    # Check if export script exists
    export_script = Path("rl/export_onnx.py")
    if not export_script.exists():
        print("✗ Export script not found")
        return False
    
    # Run export
    result = run_command("cd rl && python export_onnx.py --input ppo_bus_final --output ppo_bus_policy.onnx", "Exporting to ONNX")
    return result is not None

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    
    directories = [
        "logs",
        "models",
        "data/gtfs_samples",
        "results",
        "eval_results"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def setup_environment():
    """Set up environment variables and configuration"""
    print("Setting up environment...")
    
    # Create .env file
    env_content = """# Bus Dispatch RL Environment Configuration
API_HOST=0.0.0.0
API_PORT=8000
WS_URL=ws://localhost:8000/live
LOG_LEVEL=INFO
SIMULATION_SPEED=1.0
MAX_EPISODE_TIME=300.0
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✓ Created .env file")

def verify_installation():
    """Verify that all components are properly installed"""
    print("Verifying installation...")
    
    checks = [
        ("Python packages", "python -c 'import stable_baselines3, torch, fastapi, uvicorn'"),
        ("Environment module", "python -c 'from env.wrappers import BusDispatchEnv'"),
        ("RL module", "python -c 'from rl.train import train_ppo_policy'"),
        ("Server module", "python -c 'from server.fastapi_server import app'"),
    ]
    
    all_passed = True
    for name, command in checks:
        result = run_command(command, f"Checking {name}")
        if result is None:
            all_passed = False
    
    return all_passed

def run_demo_test():
    """Run a quick demo test"""
    print("Running demo test...")
    
    # Test environment creation
    test_script = """
import sys
sys.path.append('.')
from env.wrappers import BusDispatchEnv

# Create environment
env = BusDispatchEnv(
    grid_size=(20, 20),
    num_stops=32,
    num_buses=6,
    time_step=0.5,
    max_episode_time=60.0,
    seed=42
)

# Test reset
obs = env.reset()
print(f"Environment created successfully. Observation shape: {obs.shape}")

# Test step
action = [0] * env.num_buses
obs, reward, done, info = env.step(action)
print(f"Environment step successful. Reward: {reward}")

print("✓ Environment test passed")
"""
    
    with open("test_env.py", "w") as f:
        f.write(test_script)
    
    result = run_command("python test_env.py", "Testing environment")
    
    # Clean up
    if os.path.exists("test_env.py"):
        os.remove("test_env.py")
    
    return result is not None

def create_startup_scripts():
    """Create startup scripts for different components"""
    print("Creating startup scripts...")
    
    # Server startup script
    server_script = """#!/bin/bash
echo "Starting Bus Dispatch RL Server..."
cd server
python fastapi_server.py
"""
    
    with open("start_server.sh", "w") as f:
        f.write(server_script)
    
    os.chmod("start_server.sh", 0o755)
    print("✓ Created start_server.sh")
    
    # Training script
    training_script = """#!/bin/bash
echo "Training RL model..."
cd rl
python train.py --mode train --timesteps 100000
"""
    
    with open("train_model.sh", "w") as f:
        f.write(training_script)
    
    os.chmod("train_model.sh", 0o755)
    print("✓ Created train_model.sh")
    
    # Demo script
    demo_script = """#!/bin/bash
echo "Running demo scenario..."
cd scripts
python demo_seed.py --scenario morning_rush --mode rl --render
"""
    
    with open("run_demo.sh", "w") as f:
        f.write(demo_script)
    
    os.chmod("run_demo.sh", 0o755)
    print("✓ Created run_demo.sh")

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup Bus Dispatch RL MVP")
    parser.add_argument("--skip-training", action="store_true", help="Skip RL model training")
    parser.add_argument("--skip-export", action="store_true", help="Skip ONNX export")
    parser.add_argument("--quick", action="store_true", help="Quick setup (minimal training)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BUS DISPATCH RL MVP SETUP")
    print("=" * 60)
    print()
    
    # Setup steps
    steps = [
        ("Creating directories", create_directories),
        ("Installing dependencies", install_dependencies),
        ("Setting up environment", setup_environment),
        ("Verifying installation", verify_installation),
        ("Running demo test", run_demo_test),
        ("Creating startup scripts", create_startup_scripts),
    ]
    
    # Add training steps if not skipped
    if not args.skip_training:
        if args.quick:
            steps.append(("Training RL model (quick)", lambda: run_command("cd rl && python train.py --mode train --timesteps 10000", "Quick training")))
        else:
            steps.append(("Training RL model", train_rl_model))
    
    if not args.skip_export:
        steps.append(("Exporting ONNX model", export_onnx_model))
    
    # Run all steps
    success_count = 0
    total_steps = len(steps)
    
    for step_name, step_func in steps:
        print(f"\n{success_count + 1}/{total_steps}: {step_name}")
        if step_func():
            success_count += 1
        else:
            print(f"✗ {step_name} failed")
    
    # Summary
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    print(f"Completed: {success_count}/{total_steps} steps")
    
    if success_count == total_steps:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the server: ./start_server.sh")
        print("2. Open dashboard: http://localhost:8000")
        print("3. Run demo: ./run_demo.sh")
    else:
        print("✗ Setup incomplete. Please check errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
