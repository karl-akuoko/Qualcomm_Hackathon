#!/usr/bin/env python3
"""
Start the destination-aware bus dispatch system
"""

import os
import sys
import subprocess
import time
import signal
import psutil

def kill_existing_servers():
    """Kill any existing servers on port 8000"""
    print("🔧 Killing existing servers...")
    
    try:
        # Find processes using port 8000
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info['connections'] or []:
                    if conn.laddr.port == 8000:
                        print(f"✓ Killing process {proc.info['pid']} on port 8000")
                        proc.kill()
                        time.sleep(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Additional check with lsof
        try:
            result = subprocess.run(['lsof', '-ti', ':8000'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        print(f"✓ Killing process {pid} on port 8000")
                        subprocess.run(['kill', '-9', pid], capture_output=True)
        except:
            pass
        
        print("✓ Port 8000 cleared")
        
    except Exception as e:
        print(f"⚠ Error killing servers: {e}")

def start_destination_fix_server():
    """Start the destination-aware server"""
    print("🚀 Starting destination-aware bus dispatch system...")
    
    try:
        # Start the server
        server_process = subprocess.Popen([
            sys.executable, 'server/fastapi_destination_fix.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if server is running
        if server_process.poll() is None:
            print("✅ Destination-aware server started successfully!")
            print("🌐 Server: http://localhost:8000")
            print("✅ Destination-aware routing: buses go to passenger destinations")
            print("✅ Fixed passenger drop-off mechanics")
            print("✅ Wait time = arrival to destination (not just pickup)")
            print("✅ Press Ctrl+C to stop")
            return server_process
        else:
            stdout, stderr = server_process.communicate()
            print(f"❌ Server failed to start:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return None

def main():
    """Main startup function"""
    print("=" * 60)
    print("STARTING DESTINATION-AWARE BUS DISPATCH SYSTEM")
    print("=" * 60)
    
    # Kill existing servers
    kill_existing_servers()
    
    # Start destination-aware server
    server_process = start_destination_fix_server()
    
    if server_process:
        try:
            # Keep server running
            server_process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down server...")
            server_process.terminate()
            server_process.wait()
            print("✅ Server stopped")
    else:
        print("❌ Failed to start server")
        sys.exit(1)

if __name__ == "__main__":
    main()
