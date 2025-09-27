#!/usr/bin/env python3
"""
Simple demo runner - just runs the simulation
"""

import sys
import os
import time
import numpy as np

# Add paths
sys.path.append('.')
sys.path.append('env')

def run_simple_demo():
    """Run a simple demo without server"""
    print("=" * 50)
    print("BUS DISPATCH RL - SIMPLE DEMO")
    print("=" * 50)
    
    try:
        from env.wrappers import BusDispatchEnv
        
        # Create environment
        print("Creating environment...")
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,
            max_episode_time=120.0,
            seed=42
        )
        
        # Reset
        obs = env.reset()
        print(f"✓ Environment created. Observation shape: {obs.shape}")
        
        # Run simulation
        print("\nRunning simulation...")
        print("Time | RL Avg Wait | Baseline Avg Wait | Improvement")
        print("-" * 60)
        
        step = 0
        while step < 240:  # 2 minutes of simulation
            # Random actions (in real demo, this would be RL policy)
            action = np.random.randint(0, 4, size=env.num_buses)
            
            # Step environment
            obs, reward, done, info = env.step(action)
            
            # Print progress every 10 steps
            if step % 10 == 0:
                time_min = env.current_time
                rl_wait = info.get('rl_stats', {}).get('avg_wait', 0)
                baseline_wait = info.get('baseline_stats', {}).get('avg_wait', 0)
                
                if baseline_wait > 0:
                    improvement = (baseline_wait - rl_wait) / baseline_wait * 100
                else:
                    improvement = 0
                
                print(f"{time_min:4.1f} | {rl_wait:8.2f} | {baseline_wait:13.2f} | {improvement:8.1f}%")
            
            step += 1
            
            if done:
                break
        
        # Final results
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        
        final_info = env._get_info()
        rl_stats = final_info.get('rl_stats', {})
        baseline_stats = final_info.get('baseline_stats', {})
        improvements = final_info.get('improvements', {})
        
        print(f"RL Performance:")
        print(f"  Average Wait: {rl_stats.get('avg_wait', 0):.2f} minutes")
        print(f"  Load Std Dev: {rl_stats.get('load_std', 0):.2f}")
        
        print(f"\nBaseline Performance:")
        print(f"  Average Wait: {baseline_stats.get('avg_wait', 0):.2f} minutes")
        print(f"  Load Std Dev: {baseline_stats.get('load_std', 0):.2f}")
        
        print(f"\nImprovements:")
        print(f"  Wait Time: {improvements.get('avg_wait', 0)*100:.1f}%")
        print(f"  Overcrowding: {improvements.get('overcrowd', 0)*100:.1f}%")
        
        # Check if we meet MVP criteria
        wait_improvement = improvements.get('avg_wait', 0)
        overcrowd_improvement = improvements.get('overcrowd', 0)
        
        print(f"\nMVP Success Criteria:")
        print(f"  ≥20% wait improvement: {'✓' if wait_improvement >= 0.2 else '✗'} ({wait_improvement*100:.1f}%)")
        print(f"  ≥30% overcrowd improvement: {'✓' if overcrowd_improvement >= 0.3 else '✗'} ({overcrowd_improvement*100:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    if not os.path.exists('env/wrappers.py'):
        print("✗ Please run this from the reroute directory")
        return 1
    
    success = run_simple_demo()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
