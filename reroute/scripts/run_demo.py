#!/usr/bin/env python3
"""
Complete demo runner script.
Starts all services and runs the demo automatically.
"""

import os
import sys
import time
import subprocess
import signal
import threading
from pathlib import Path


class DemoRunner:
    """Manages the complete demo execution."""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_server(self):
        """Start the FastAPI server."""
        print("🚀 Starting simulation server...")
        
        server_process = subprocess.Popen(
            ["python3", "-m", "server.api"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.processes.append(("server", server_process))
        
        # Wait for server to start
        time.sleep(3)
        
        if server_process.poll() is None:
            print("✅ Server started on http://localhost:8000")
            return True
        else:
            print("❌ Server failed to start")
            return False
    
    def start_dashboard(self):
        """Start the web dashboard."""
        print("🖥️ Starting web dashboard...")
        
        dashboard_dir = Path("clients/dashboard")
        if not dashboard_dir.exists():
            print("❌ Dashboard directory not found")
            return False
        
        dashboard_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=dashboard_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        self.processes.append(("dashboard", dashboard_process))
        
        # Wait for dashboard to start
        time.sleep(5)
        
        if dashboard_process.poll() is None:
            print("✅ Dashboard started on http://localhost:3000")
            return True
        else:
            print("❌ Dashboard failed to start")
            return False
    
    def run_demo_script(self):
        """Run the demo script."""
        print("🎬 Running demo script...")
        
        demo_process = subprocess.Popen(
            ["python3", "scripts/demo_seed.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Stream output in real-time
        while demo_process.poll() is None and self.running:
            output = demo_process.stdout.readline()
            if output:
                print(output.strip())
            time.sleep(0.1)
        
        # Get remaining output
        stdout, stderr = demo_process.communicate()
        if stdout:
            print(stdout)
        if stderr:
            print("Demo errors:", stderr)
        
        return demo_process.returncode == 0
    
    def stop_all_processes(self):
        """Stop all running processes."""
        print("\n🛑 Stopping all processes...")
        
        for name, process in self.processes:
            if process.poll() is None:
                print(f"Stopping {name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Force killing {name}...")
                    process.kill()
        
        self.running = False
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        print(f"\nReceived signal {signum}")
        self.stop_all_processes()
        sys.exit(0)
    
    def run(self):
        """Run the complete demo."""
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            print("🚌 Bus Routing Demo Runner")
            print("=" * 40)
            
            # Check if setup is complete
            if not Path("models/final_model.zip").exists():
                print("❌ Model not found. Please run setup first:")
                print("   python scripts/setup_demo.py")
                return False
            
            # Start services
            if not self.start_server():
                return False
            
            if not self.start_dashboard():
                return False
            
            print("\n📋 Demo services started successfully!")
            print("Dashboard: http://localhost:3000")
            print("API: http://localhost:8000")
            print("\nPress Ctrl+C to stop the demo")
            
            # Wait a bit for services to stabilize
            time.sleep(2)
            
            # Run the demo
            demo_success = self.run_demo_script()
            
            if demo_success:
                print("\n🎉 Demo completed successfully!")
            else:
                print("\n❌ Demo encountered errors")
            
            return demo_success
            
        except KeyboardInterrupt:
            print("\n\nDemo interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            return False
        finally:
            self.stop_all_processes()


def main():
    """Main entry point."""
    runner = DemoRunner()
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()