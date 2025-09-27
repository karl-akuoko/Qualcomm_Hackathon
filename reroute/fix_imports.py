#!/usr/bin/env python3
"""
Fix import issues in the codebase
"""

import os
import sys

def fix_gym_imports():
    """Fix gym imports to use gymnasium"""
    files_to_check = [
        'env/wrappers.py',
        'rl/train.py', 
        'rl/eval.py',
        'rl/export_onnx.py',
        'rl/policies.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"Checking {file_path}...")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Fix gym imports
            if 'import gym' in content and 'import gymnasium' not in content:
                content = content.replace('import gym', 'import gymnasium as gym')
                print(f"  Fixed: import gym -> import gymnasium as gym")
            
            if 'from gym import' in content:
                content = content.replace('from gym import', 'from gymnasium import')
                print(f"  Fixed: from gym import -> from gymnasium import")
            
            # Write back if changes were made
            if content != open(file_path, 'r').read():
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"  ✓ Updated {file_path}")

def create_simple_requirements():
    """Create a simple requirements.txt"""
    requirements = """numpy>=1.21.0
gymnasium>=0.27.0
networkx>=2.8.0
matplotlib>=3.5.0
fastapi>=0.100.0
uvicorn>=0.20.0
websockets>=11.0.0
pydantic>=2.0.0
stable-baselines3>=2.0.0
torch>=1.13.0
pandas>=1.5.0
"""
    
    with open('requirements_simple.txt', 'w') as f:
        f.write(requirements)
    
    print("✓ Created requirements_simple.txt")

def main():
    """Fix all import issues"""
    print("Fixing import issues...")
    
    # Fix gym imports
    fix_gym_imports()
    
    # Create simple requirements
    create_simple_requirements()
    
    print("\n✓ Import fixes complete!")
    print("Now run: pip install -r requirements_simple.txt")

if __name__ == "__main__":
    main()
