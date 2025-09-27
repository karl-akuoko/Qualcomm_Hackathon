#!/usr/bin/env python3
"""
Simple installation script - just installs what's needed
"""

import subprocess
import sys
import os

def install_package(package):
    """Install a Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package}")
        return False

def main():
    """Install required packages"""
    print("Installing required packages...")
    
    packages = [
        "numpy",
        "fastapi", 
        "uvicorn",
        "websockets",
        "pydantic",
        "stable-baselines3",
        "torch",
        "gymnasium",
        "networkx",
        "matplotlib",
        "pandas",
        "onnx",
        "onnxruntime"
    ]
    
    success = 0
    for package in packages:
        if install_package(package):
            success += 1
    
    print(f"\nInstalled {success}/{len(packages)} packages")
    
    if success == len(packages):
        print("✓ All packages installed successfully!")
        print("Now run: python start_simple.py")
    else:
        print("✗ Some packages failed to install")
        print("You may need to install them manually")

if __name__ == "__main__":
    main()
