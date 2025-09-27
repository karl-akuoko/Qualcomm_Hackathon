#!/usr/bin/env python3
"""
Setup script for the bus routing demo.
Initializes the environment, trains a model, and prepares for demo.
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_command(command, description, cwd=None):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            cwd=cwd,
            capture_output=True, 
            text=True
        )
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_python_version():
    """Check Python version compatibility."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True


def setup_python_environment():
    """Install Python dependencies."""
    return run_command(
        "pip install -r requirements.txt",
        "Installing Python dependencies"
    )


def train_model():
    """Train the RL model."""
    # Create models directory
    os.makedirs("models", exist_ok=True)
    
    # Train with reduced timesteps for demo
    train_command = """
    python3 -c "
from rl.train import BusRoutingTrainer
trainer = BusRoutingTrainer()
config = trainer._get_default_config()
config['total_timesteps'] = 10000  # Very reduced for demo
config['eval_freq'] = 2000
config['n_steps'] = 512
trainer.config = config
trainer.train(save_best=False, early_stopping=False)
print('Training completed')
"
    """
    
    return run_command(
        train_command,
        "Training RL model (this may take several minutes)"
    )


def export_onnx_model():
    """Export trained model to ONNX."""
    export_command = """
    python3 -c "
from rl.export_onnx import export_model_pipeline
export_info = export_model_pipeline('./models/final_model.zip')
print('ONNX export completed:', export_info)
"
    """
    
    return run_command(
        export_command,
        "Exporting model to ONNX format"
    )


def setup_dashboard():
    """Setup the web dashboard."""
    dashboard_dir = Path("clients/dashboard")
    
    if not dashboard_dir.exists():
        print("❌ Dashboard directory not found")
        return False
    
    # Install npm dependencies
    if not run_command("npm install", "Installing dashboard dependencies", cwd=dashboard_dir):
        return False
    
    return True


def setup_mobile():
    """Setup the mobile app."""
    mobile_dir = Path("clients/mobile")
    
    if not mobile_dir.exists():
        print("❌ Mobile app directory not found")
        return False
    
    # Install npm dependencies
    if not run_command("npm install", "Installing mobile app dependencies", cwd=mobile_dir):
        return False
    
    return True


def create_demo_config():
    """Create demo configuration file."""
    config = {
        "demo": {
            "seed": 42,
            "duration_seconds": 300,
            "stress_tests": ["closure", "surge"],
            "target_improvement": 20
        },
        "server": {
            "host": "localhost",
            "port": 8000,
            "websocket_path": "/ws/live"
        },
        "dashboard": {
            "port": 3000,
            "update_rate_hz": 5
        }
    }
    
    import json
    with open("demo_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("✅ Demo configuration created")
    return True


def verify_setup():
    """Verify the setup is complete."""
    required_files = [
        "models/final_model.zip",
        "models/onnx/final_model_optimized.onnx",
        "demo_config.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ Setup verification passed")
    return True


def main():
    """Main setup function."""
    print("🚌 Bus Routing Demo Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Setup steps
    steps = [
        ("Installing Python dependencies", setup_python_environment),
        ("Training RL model", train_model),
        ("Exporting ONNX model", export_onnx_model),
        ("Setting up dashboard", setup_dashboard),
        ("Setting up mobile app", setup_mobile),
        ("Creating demo config", create_demo_config),
        ("Verifying setup", verify_setup)
    ]
    
    for description, func in steps:
        print(f"\n📋 {description}")
        if not func():
            print(f"\n❌ Setup failed at: {description}")
            sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the server: python3 -m server.api")
    print("2. Start the dashboard: cd clients/dashboard && npm run dev")
    print("3. Run the demo: python3 scripts/demo_seed.py")
    print("\nDemo will be available at:")
    print("- Dashboard: http://localhost:3000")
    print("- API: http://localhost:8000")
    print("- Mobile: Follow React Native setup guide")


if __name__ == "__main__":
    main()