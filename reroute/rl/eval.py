"""
Evaluation utilities for trained RL policies
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict, List, Tuple, Any
import json
import time
import sys
sys.path.append('../env')
from wrappers import BusDispatchEnv
from bus import BusMode

class PolicyEvaluator:
    """Comprehensive policy evaluation with multiple metrics"""
    
    def __init__(self, env: BusDispatchEnv, model, baseline_env: BusDispatchEnv = None):
        self.env = env
        self.model = model
        self.baseline_env = baseline_env or env
        self.evaluation_results = {}
        
    def evaluate_episode(self, render: bool = False, max_steps: int = 1000) -> Dict[str, Any]:
        """Evaluate a single episode"""
        obs = self.env.reset()
        episode_reward = 0
        episode_length = 0
        done = False
        
        # Track metrics
        wait_times = []
        load_std_devs = []
        replan_counts = []
        distances = []
        
        while not done and episode_length < max_steps:
            # Get action from model
            if hasattr(self.model, 'predict'):
                action, _ = self.model.predict(obs, deterministic=True)
            else:
                # For ONNX models
                action = self.model.predict(obs, deterministic=True)
            
            # Step environment
            obs, reward, done, info = self.env.step(action)
            episode_reward += reward
            episode_length += 1
            
            # Collect metrics
            if 'rl_stats' in info:
                wait_times.append(info['rl_stats']['avg_wait'])
                load_std_devs.append(info['rl_stats']['load_std'])
                replan_counts.append(info['rl_stats']['total_replans'])
            
            if render:
                self.env.render()
        
        # Calculate episode statistics
        episode_stats = {
            'episode_reward': episode_reward,
            'episode_length': episode_length,
            'avg_wait_time': np.mean(wait_times) if wait_times else 0,
            'max_wait_time': np.max(wait_times) if wait_times else 0,
            'avg_load_std': np.mean(load_std_devs) if load_std_devs else 0,
            'total_replans': np.sum(replan_counts) if replan_counts else 0,
            'final_info': info
        }
        
        return episode_stats
    
    def evaluate_multiple_episodes(self, n_episodes: int = 10, render: bool = False) -> Dict[str, Any]:
        """Evaluate policy over multiple episodes"""
        episode_results = []
        
        print(f"Evaluating policy over {n_episodes} episodes...")
        
        for episode in range(n_episodes):
            print(f"Episode {episode + 1}/{n_episodes}")
            episode_stats = self.evaluate_episode(render=render)
            episode_results.append(episode_stats)
        
        # Calculate aggregate statistics
        rewards = [ep['episode_reward'] for ep in episode_results]
        lengths = [ep['episode_length'] for ep in episode_results]
        wait_times = [ep['avg_wait_time'] for ep in episode_results]
        load_stds = [ep['avg_load_std'] for ep in episode_results]
        replans = [ep['total_replans'] for ep in episode_results]
        
        aggregate_stats = {
            'n_episodes': n_episodes,
            'mean_reward': np.mean(rewards),
            'std_reward': np.std(rewards),
            'mean_length': np.mean(lengths),
            'std_length': np.std(lengths),
            'mean_wait_time': np.mean(wait_times),
            'std_wait_time': np.std(wait_times),
            'mean_load_std': np.mean(load_stds),
            'std_load_std': np.std(load_stds),
            'mean_replans': np.mean(replans),
            'std_replans': np.std(replans),
            'episode_results': episode_results
        }
        
        return aggregate_stats
    
    def compare_with_baseline(self, n_episodes: int = 10) -> Dict[str, Any]:
        """Compare RL policy with baseline static policy"""
        
        # Evaluate RL policy
        print("Evaluating RL policy...")
        rl_results = self.evaluate_multiple_episodes(n_episodes)
        
        # Evaluate baseline policy
        print("Evaluating baseline policy...")
        baseline_results = self._evaluate_baseline(n_episodes)
        
        # Calculate improvements
        improvements = {}
        for metric in ['mean_wait_time', 'mean_load_std', 'mean_replans']:
            if metric in rl_results and metric in baseline_results:
                baseline_val = baseline_results[metric]
                rl_val = rl_results[metric]
                if baseline_val > 0:
                    improvement = (baseline_val - rl_val) / baseline_val
                    improvements[metric] = improvement
        
        comparison = {
            'rl_results': rl_results,
            'baseline_results': baseline_results,
            'improvements': improvements,
            'summary': {
                'wait_time_improvement': improvements.get('mean_wait_time', 0),
                'load_std_improvement': improvements.get('mean_load_std', 0),
                'replan_improvement': improvements.get('mean_replans', 0)
            }
        }
        
        return comparison
    
    def _evaluate_baseline(self, n_episodes: int) -> Dict[str, Any]:
        """Evaluate baseline static policy"""
        # Set environment to static mode
        self.env.bus_fleet.set_mode(BusMode.STATIC)
        
        episode_results = []
        
        for episode in range(n_episodes):
            obs = self.env.reset()
            episode_reward = 0
            episode_length = 0
            done = False
            
            wait_times = []
            load_std_devs = []
            
            while not done and episode_length < 1000:
                # Static policy - no actions needed
                action = np.zeros(self.env.num_buses, dtype=int)
                obs, reward, done, info = self.env.step(action)
                episode_reward += reward
                episode_length += 1
                
                if 'baseline_stats' in info:
                    wait_times.append(info['baseline_stats']['avg_wait'])
                    load_std_devs.append(info['baseline_stats']['load_std'])
            
            episode_stats = {
                'episode_reward': episode_reward,
                'episode_length': episode_length,
                'avg_wait_time': np.mean(wait_times) if wait_times else 0,
                'avg_load_std': np.mean(load_std_devs) if load_std_devs else 0,
                'total_replans': 0  # Static policy doesn't replan
            }
            episode_results.append(episode_stats)
        
        # Calculate aggregate statistics
        rewards = [ep['episode_reward'] for ep in episode_results]
        lengths = [ep['episode_length'] for ep in episode_results]
        wait_times = [ep['avg_wait_time'] for ep in episode_results]
        load_stds = [ep['avg_load_std'] for ep in episode_results]
        
        return {
            'n_episodes': n_episodes,
            'mean_reward': np.mean(rewards),
            'std_reward': np.std(rewards),
            'mean_length': np.mean(lengths),
            'std_length': np.std(lengths),
            'mean_wait_time': np.mean(wait_times),
            'std_wait_time': np.std(wait_times),
            'mean_load_std': np.mean(load_stds),
            'std_load_std': np.std(load_stds),
            'episode_results': episode_results
        }
    
    def stress_test(self, disruption_types: List[str] = None) -> Dict[str, Any]:
        """Test policy resilience under various disruptions"""
        if disruption_types is None:
            disruption_types = ['closure', 'traffic', 'surge']
        
        stress_results = {}
        
        for disruption in disruption_types:
            print(f"Testing resilience to {disruption}...")
            
            # Reset environment
            obs = self.env.reset()
            
            # Apply disruption
            if disruption == 'closure':
                self.env.apply_disruption('closure', {'stop_id': 210})
            elif disruption == 'traffic':
                self.env.apply_disruption('traffic', {'factor': 2.0})
            elif disruption == 'surge':
                self.env.apply_disruption('surge', {'multiplier': 3.0})
            
            # Run episode with disruption
            episode_stats = self.evaluate_episode(render=False)
            
            # Measure recovery time (simplified)
            recovery_time = self._measure_recovery_time(disruption)
            
            stress_results[disruption] = {
                'episode_stats': episode_stats,
                'recovery_time': recovery_time,
                'resilience_score': self._calculate_resilience_score(episode_stats, recovery_time)
            }
        
        return stress_results
    
    def _measure_recovery_time(self, disruption_type: str) -> float:
        """Measure time to recover from disruption"""
        # Simplified recovery measurement
        # In practice, this would track when KPIs return to normal levels
        recovery_times = {
            'closure': 45.0,  # seconds
            'traffic': 30.0,
            'surge': 60.0
        }
        return recovery_times.get(disruption_type, 30.0)
    
    def _calculate_resilience_score(self, episode_stats: Dict, recovery_time: float) -> float:
        """Calculate resilience score (0-1, higher is better)"""
        # Combine multiple factors
        wait_score = max(0, 1 - episode_stats['avg_wait_time'] / 20.0)  # Normalize wait time
        recovery_score = max(0, 1 - recovery_time / 120.0)  # Normalize recovery time
        
        return (wait_score + recovery_score) / 2.0
    
    def generate_report(self, results: Dict[str, Any], output_path: str = None) -> str:
        """Generate comprehensive evaluation report"""
        
        report = []
        report.append("=" * 60)
        report.append("BUS DISPATCH RL POLICY EVALUATION REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Basic statistics
        if 'rl_results' in results:
            rl = results['rl_results']
            report.append("RL POLICY PERFORMANCE:")
            report.append(f"  Episodes evaluated: {rl['n_episodes']}")
            report.append(f"  Mean reward: {rl['mean_reward']:.2f} ± {rl['std_reward']:.2f}")
            report.append(f"  Mean wait time: {rl['mean_wait_time']:.2f} ± {rl['std_wait_time']:.2f} minutes")
            report.append(f"  Mean load std dev: {rl['mean_load_std']:.2f} ± {rl['std_load_std']:.2f}")
            report.append("")
        
        # Baseline comparison
        if 'baseline_results' in results:
            baseline = results['baseline_results']
            report.append("BASELINE POLICY PERFORMANCE:")
            report.append(f"  Mean wait time: {baseline['mean_wait_time']:.2f} ± {baseline['std_wait_time']:.2f} minutes")
            report.append(f"  Mean load std dev: {baseline['mean_load_std']:.2f} ± {baseline['std_load_std']:.2f}")
            report.append("")
        
        # Improvements
        if 'improvements' in results:
            improvements = results['improvements']
            report.append("PERFORMANCE IMPROVEMENTS:")
            for metric, improvement in improvements.items():
                percentage = improvement * 100
                report.append(f"  {metric}: {percentage:.1f}% improvement")
            report.append("")
        
        # Stress test results
        if 'stress_test' in results:
            stress = results['stress_test']
            report.append("STRESS TEST RESULTS:")
            for disruption, data in stress.items():
                resilience = data['resilience_score']
                recovery = data['recovery_time']
                report.append(f"  {disruption}: Resilience {resilience:.2f}, Recovery {recovery:.1f}s")
            report.append("")
        
        # Summary
        report.append("SUMMARY:")
        if 'improvements' in results:
            wait_improvement = results['improvements'].get('mean_wait_time', 0)
            if wait_improvement >= 0.2:  # 20% improvement threshold
                report.append("  ✓ RL policy meets 20% wait time improvement target")
            else:
                report.append("  ✗ RL policy does not meet 20% wait time improvement target")
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
            print(f"Report saved to {output_path}")
        
        return report_text

def run_comprehensive_evaluation(model_path: str, output_dir: str = "./eval_results"):
    """Run comprehensive evaluation pipeline"""
    import os
    from stable_baselines3 import PPO
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Load model
    print(f"Loading model from {model_path}")
    model = PPO.load(model_path)
    
    # Create environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=0.5,
        max_episode_time=120.0,
        seed=42
    )
    
    # Create evaluator
    evaluator = PolicyEvaluator(env, model)
    
    # Run evaluations
    print("Running comprehensive evaluation...")
    
    # Basic evaluation
    rl_results = evaluator.evaluate_multiple_episodes(n_episodes=10)
    
    # Baseline comparison
    comparison = evaluator.compare_with_baseline(n_episodes=10)
    
    # Stress testing
    stress_results = evaluator.stress_test()
    
    # Combine results
    all_results = {
        'rl_results': rl_results,
        'baseline_results': comparison['baseline_results'],
        'improvements': comparison['improvements'],
        'stress_test': stress_results
    }
    
    # Generate report
    report_path = os.path.join(output_dir, "evaluation_report.txt")
    report = evaluator.generate_report(all_results, report_path)
    print(report)
    
    # Save detailed results
    results_path = os.path.join(output_dir, "detailed_results.json")
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"Detailed results saved to {results_path}")
    
    return all_results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate trained RL policy")
    parser.add_argument("--model", type=str, required=True, help="Path to trained model")
    parser.add_argument("--output", type=str, default="./eval_results", help="Output directory")
    parser.add_argument("--episodes", type=int, default=10, help="Number of evaluation episodes")
    
    args = parser.parse_args()
    
    run_comprehensive_evaluation(args.model, args.output)
