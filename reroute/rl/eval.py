"""
Evaluation and benchmarking tools for trained RL models.
Includes performance comparison, visualization, and demo generation.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import json
import time
from dataclasses import dataclass

from stable_baselines3 import PPO
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.wrappers import BusRoutingEnv
from rl.export_onnx import ONNXInference


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""
    avg_wait_time: float
    p90_wait_time: float
    load_std: float
    overcrowd_ratio: float
    total_replans: int
    replan_frequency: float
    fuel_efficiency: float
    total_reward: float
    episode_length: int


class ModelEvaluator:
    """Comprehensive model evaluation and comparison."""
    
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = model_dir
        self.results_dir = os.path.join(model_dir, "evaluation")
        os.makedirs(self.results_dir, exist_ok=True)
    
    def evaluate_model(self,
                      model_path: str,
                      n_episodes: int = 10,
                      seed: int = 42,
                      disruption_scenarios: List[str] = None) -> Dict:
        """
        Comprehensive model evaluation.
        
        Args:
            model_path: Path to trained model
            n_episodes: Number of evaluation episodes
            seed: Random seed
            disruption_scenarios: List of disruption scenarios to test
        
        Returns:
            evaluation_results: Dictionary with comprehensive metrics
        """
        if disruption_scenarios is None:
            disruption_scenarios = ["none", "closure", "traffic", "surge"]
        
        print(f"Evaluating model: {model_path}")
        print(f"Episodes: {n_episodes}, Scenarios: {disruption_scenarios}")
        
        # Load model
        model = PPO.load(model_path)
        
        results = {}
        
        for scenario in disruption_scenarios:
            print(f"\nTesting scenario: {scenario}")
            
            scenario_results = self._evaluate_scenario(
                model, scenario, n_episodes, seed
            )
            results[scenario] = scenario_results
        
        # Calculate summary statistics
        summary = self._calculate_summary(results)
        results['summary'] = summary
        
        # Save results
        self._save_results(results, model_path)
        
        return results
    
    def _evaluate_scenario(self,
                          model: PPO,
                          scenario: str,
                          n_episodes: int,
                          seed: int) -> Dict:
        """Evaluate model on specific disruption scenario."""
        episode_metrics = []
        
        for episode in range(n_episodes):
            # Create environment with specific seed
            env = BusRoutingEnv(seed=seed + episode)
            
            # Apply scenario
            if scenario == "closure":
                env.trigger_disruption("closure")
            elif scenario == "traffic":
                env.trigger_disruption("traffic")
            elif scenario == "surge":
                env.trigger_disruption("surge")
            
            # Run episode
            metrics = self._run_episode(model, env)
            episode_metrics.append(metrics)
        
        # Calculate statistics
        return self._aggregate_episode_metrics(episode_metrics)
    
    def _run_episode(self, model: PPO, env: BusRoutingEnv) -> EvaluationMetrics:
        """Run a single evaluation episode."""
        obs = env.reset()
        done = False
        total_reward = 0
        episode_length = 0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            total_reward += reward
            episode_length += 1
        
        # Get final KPIs
        kpis = env.get_kpis()
        
        return EvaluationMetrics(
            avg_wait_time=kpis['avg_wait'],
            p90_wait_time=kpis['p90_wait'],
            load_std=kpis['load_std'],
            overcrowd_ratio=kpis['overcrowd_ratio'],
            total_replans=kpis['total_replans'],
            replan_frequency=kpis['replan_frequency'],
            fuel_efficiency=1.0 / (kpis.get('fuel_km', 1.0) + 1.0),  # Inverse fuel usage
            total_reward=total_reward,
            episode_length=episode_length
        )
    
    def _aggregate_episode_metrics(self, episode_metrics: List[EvaluationMetrics]) -> Dict:
        """Aggregate metrics across episodes."""
        metrics_dict = {}
        
        for field in EvaluationMetrics.__annotations__:
            values = [getattr(metric, field) for metric in episode_metrics]
            metrics_dict[field] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'min': np.min(values),
                'max': np.max(values),
                'values': values
            }
        
        return metrics_dict
    
    def _calculate_summary(self, results: Dict) -> Dict:
        """Calculate summary statistics across scenarios."""
        summary = {}
        
        # Key metrics for comparison
        key_metrics = ['avg_wait_time', 'p90_wait_time', 'overcrowd_ratio', 'total_reward']
        
        for metric in key_metrics:
            summary[metric] = {}
            for scenario, scenario_results in results.items():
                if scenario != 'summary' and metric in scenario_results:
                    summary[metric][scenario] = scenario_results[metric]['mean']
        
        # Calculate resilience (recovery from disruptions)
        if 'none' in summary['avg_wait_time']:
            baseline_wait = summary['avg_wait_time']['none']
            for scenario in ['closure', 'traffic', 'surge']:
                if scenario in summary['avg_wait_time']:
                    disruption_wait = summary['avg_wait_time'][scenario]
                    resilience = max(0, 1 - (disruption_wait - baseline_wait) / baseline_wait)
                    summary[f'{scenario}_resilience'] = resilience
        
        return summary
    
    def _save_results(self, results: Dict, model_path: str):
        """Save evaluation results to file."""
        model_name = os.path.basename(model_path).replace('.zip', '')
        results_path = os.path.join(self.results_dir, f"{model_name}_evaluation.json")
        
        # Convert numpy types for JSON serialization
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            else:
                return obj
        
        results_serializable = convert_numpy(results)
        
        with open(results_path, 'w') as f:
            json.dump(results_serializable, f, indent=2)
        
        print(f"Results saved to: {results_path}")
    
    def compare_models(self, model_paths: List[str], **kwargs) -> Dict:
        """Compare multiple trained models."""
        print("Comparing models...")
        
        comparison_results = {}
        
        for model_path in model_paths:
            model_name = os.path.basename(model_path).replace('.zip', '')
            print(f"\nEvaluating {model_name}...")
            
            results = self.evaluate_model(model_path, **kwargs)
            comparison_results[model_name] = results
        
        # Save comparison
        comparison_path = os.path.join(self.results_dir, "model_comparison.json")
        with open(comparison_path, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        return comparison_results
    
    def benchmark_onnx_inference(self, onnx_path: str) -> Dict:
        """Benchmark ONNX inference performance."""
        print(f"Benchmarking ONNX inference: {onnx_path}")
        
        onnx_inference = ONNXInference(onnx_path)
        benchmark_results = onnx_inference.benchmark(num_runs=1000)
        
        # Save benchmark results
        benchmark_path = os.path.join(self.results_dir, "onnx_benchmark.json")
        with open(benchmark_path, 'w') as f:
            json.dump(benchmark_results, f, indent=2)
        
        return benchmark_results


class DemoGenerator:
    """Generate demo scenarios for presentation."""
    
    def __init__(self, model_path: str, onnx_path: str = None):
        self.model_path = model_path
        self.onnx_path = onnx_path
        
        # Load models
        self.model = PPO.load(model_path)
        if onnx_path:
            self.onnx_inference = ONNXInference(onnx_path)
    
    def generate_demo_episode(self,
                            scenario: str = "morning_peak",
                            duration: int = 300,
                            seed: int = 42) -> Dict:
        """
        Generate a demo episode with specific scenario.
        
        Args:
            scenario: Demo scenario ("morning_peak", "disruption", "surge")
            duration: Episode duration in seconds
            seed: Random seed
        
        Returns:
            demo_data: Dictionary with episode data
        """
        print(f"Generating demo episode: {scenario}")
        
        # Create environment
        env = BusRoutingEnv(seed=seed)
        
        # Setup scenario
        if scenario == "morning_peak":
            # Simulate morning rush hour
            env.current_time = 7 * 3600  # 7 AM
        elif scenario == "disruption":
            # Add traffic disruption
            env.trigger_disruption("closure")
        elif scenario == "surge":
            # Add demand surge
            env.trigger_disruption("surge")
        
        # Run episode
        demo_data = {
            'scenario': scenario,
            'duration': duration,
            'seed': seed,
            'timesteps': [],
            'final_kpis': None
        }
        
        obs = env.reset()
        done = False
        timestep = 0
        
        while not done and timestep < duration:
            # Get action from model
            if self.onnx_inference:
                # Use ONNX inference
                actions, _ = self.onnx_inference.predict(obs.reshape(1, -1))
                action = actions[0]  # Remove batch dimension
            else:
                # Use PyTorch model
                action, _ = self.model.predict(obs, deterministic=True)
            
            # Step environment
            obs, reward, done, info = env.step(action)
            
            # Record state
            state_data = {
                'timestep': timestep,
                'time': env.current_time,
                'reward': reward,
                'kpis': env.get_kpis(),
                'state': env.get_state_for_ui()
            }
            demo_data['timesteps'].append(state_data)
            
            timestep += 1
        
        # Final KPIs
        demo_data['final_kpis'] = env.get_kpis()
        
        print(f"Demo episode completed: {timestep} timesteps")
        return demo_data
    
    def create_comparison_demo(self, duration: int = 300) -> Dict:
        """Create side-by-side comparison demo (RL vs Baseline)."""
        print("Creating comparison demo...")
        
        comparison_demo = {
            'duration': duration,
            'rl_episode': None,
            'baseline_episode': None,
            'comparison_metrics': None
        }
        
        # RL episode
        rl_demo = self.generate_demo_episode("morning_peak", duration)
        comparison_demo['rl_episode'] = rl_demo
        
        # Baseline episode (same seed for fair comparison)
        baseline_env = BusRoutingEnv(seed=42)
        baseline_env.set_baseline_mode(True)
        
        baseline_demo = {
            'scenario': 'baseline',
            'duration': duration,
            'seed': 42,
            'timesteps': [],
            'final_kpis': None
        }
        
        obs = baseline_env.reset()
        done = False
        timestep = 0
        
        while not done and timestep < duration:
            # Baseline: all continue actions
            action = np.zeros(baseline_env.num_buses, dtype=int)
            obs, reward, done, info = baseline_env.step(action)
            
            state_data = {
                'timestep': timestep,
                'time': baseline_env.current_time,
                'reward': reward,
                'kpis': baseline_env.get_kpis(),
                'state': baseline_env.get_state_for_ui()
            }
            baseline_demo['timesteps'].append(state_data)
            
            timestep += 1
        
        baseline_demo['final_kpis'] = baseline_env.get_kpis()
        comparison_demo['baseline_episode'] = baseline_demo
        
        # Calculate comparison metrics
        rl_kpis = rl_demo['final_kpis']
        baseline_kpis = baseline_demo['final_kpis']
        
        comparison_metrics = {}
        for metric in ['avg_wait', 'p90_wait', 'load_std']:
            if metric in rl_kpis and metric in baseline_kpis:
                rl_val = rl_kpis[metric]
                baseline_val = baseline_kpis[metric]
                
                if baseline_val > 0:
                    improvement = ((baseline_val - rl_val) / baseline_val) * 100
                    comparison_metrics[f'{metric}_improvement'] = improvement
        
        comparison_demo['comparison_metrics'] = comparison_metrics
        
        print("Comparison demo completed")
        return comparison_demo


def main():
    """Main evaluation script."""
    model_path = "./models/final_model.zip"
    onnx_path = "./models/onnx/final_model_optimized.onnx"
    
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        print("Please train a model first")
        return
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Evaluate model
    results = evaluator.evaluate_model(model_path)
    
    # Benchmark ONNX if available
    if os.path.exists(onnx_path):
        benchmark_results = evaluator.benchmark_onnx_inference(onnx_path)
        print(f"ONNX Benchmark Results: {benchmark_results}")
    
    # Generate demo
    demo_generator = DemoGenerator(model_path, onnx_path if os.path.exists(onnx_path) else None)
    demo = demo_generator.create_comparison_demo()
    
    # Save demo
    demo_path = "./models/evaluation/demo.json"
    with open(demo_path, 'w') as f:
        json.dump(demo, f, indent=2)
    
    print(f"Demo saved to: {demo_path}")
    print("Evaluation completed!")


if __name__ == "__main__":
    main()
