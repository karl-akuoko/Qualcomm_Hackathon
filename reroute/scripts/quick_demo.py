#!/usr/bin/env python3
"""
Quick demo script that starts the server and dashboard for manual demonstration.
Skips training and ONNX export for immediate demo capability.
"""

import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(command, description, cwd=None, background=False):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        if background:
            process = subprocess.Popen(
                command, 
                shell=True, 
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(2)  # Give it time to start
            return process
        else:
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
        if not background:
            print(f"Error output: {e.stderr}")
        return False


def main():
    """Quick demo setup."""
    print("🚌 Quick Bus Routing Demo Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("requirements.txt").exists():
        print("❌ Please run this from the reroute directory")
        sys.exit(1)
    
    # Create a simple trained model for demo
    print("\n📋 Creating demo model...")
    
    # Create models directory
    os.makedirs("models", exist_ok=True)
    
    # Create a simple demo model file (placeholder)
    demo_model_content = """
# This is a placeholder for the demo
# In a real demo, this would be a trained PPO model
print("Demo model placeholder created")
"""
    
    with open("models/demo_model.py", "w") as f:
        f.write(demo_model_content)
    
    print("✅ Demo model placeholder created")
    
    # Start the server
    print("\n🚀 Starting simulation server...")
    server_process = run_command(
        "python3 -m server.api",
        "Starting FastAPI server",
        background=True
    )
    
    if not server_process:
        print("❌ Failed to start server")
        sys.exit(1)
    
    print("✅ Server started on http://localhost:8000")
    
    # Start the dashboard
    print("\n🖥️ Starting web dashboard...")
    dashboard_process = run_command(
        "npm run dev",
        "Starting React dashboard",
        cwd="clients/dashboard",
        background=True
    )
    
    if not dashboard_process:
        print("❌ Failed to start dashboard")
        server_process.terminate()
        sys.exit(1)
    
    print("✅ Dashboard started on http://localhost:3000")
    
    print("\n🎉 Quick demo setup completed!")
    print("\nDemo is now running:")
    print("- Dashboard: http://localhost:3000")
    print("- API: http://localhost:8000")
    print("- API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop the demo")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping demo...")
        
        # Stop processes
        if server_process:
            server_process.terminate()
        if dashboard_process:
            dashboard_process.terminate()
        
        print("✅ Demo stopped")


if __name__ == "__main__":
    main()