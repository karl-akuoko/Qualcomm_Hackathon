"""
PPO training pipeline for bus routing optimization.
Uses Stable Baselines3 for training the RL policy.
"""

import os
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.vec_env import VecMonitor
from stable_baselines3.common.logger import configure
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
import json
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.wrappers import BusRoutingEnv


class BusRoutingTrainer:
    """Trainer class for bus routing RL policy."""
    
    def __init__(self, 
                 config: Dict = None,
                 log_dir: str = "./logs",
                 model_dir: str = "./models"):
        
        self.config = config or self._get_default_config()
        self.log_dir = log_dir
        self.model_dir = model_dir
        
        # Create directories
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize environment and model
        self.env = None
        self.model = None
        self.training_history = []
        
    def _get_default_config(self) -> Dict:
        """Get default training configuration."""
        return {
            'grid_size': 20,
            'num_buses': 6,
            'num_stops': 35,
            'bus_capacity': 50,
            'seed': 42,
            
            # PPO hyperparameters
            'learning_rate': 3e-4,
            'n_steps': 2048,
            'batch_size': 64,
            'n_epochs': 10,
            'gamma': 0.99,
            'gae_lambda': 0.95,
            'clip_range': 0.2,
            'ent_coef': 0.01,
            'vf_coef': 0.5,
            'max_grad_norm': 0.5,
            
            # Training parameters
            'total_timesteps': 100000,
            'eval_freq': 5000,
            'save_freq': 10000,
            'n_eval_episodes': 5,
            
            # Network architecture
            'policy_kwargs': {
                'net_arch': [256, 256, 128],
                'activation_fn': torch.nn.ReLU
            }
        }
    
    def create_environment(self, seed: int = None) -> BusRoutingEnv:
        """Create training environment."""
        if seed is None:
            seed = self.config['seed']
            
        env = BusRoutingEnv(
            grid_size=self.config['grid_size'],
            num_buses=self.config['num_buses'],
            num_stops=self.config['num_stops'],
            bus_capacity=self.config['bus_capacity'],
            seed=seed
        )
        
        return env
    
    def create_model(self, env) -> PPO:
        """Create PPO model."""
        model = PPO(
            "MlpPolicy",
            env,
            learning_rate=self.config['learning_rate'],
            n_steps=self.config['n_steps'],
            batch_size=self.config['batch_size'],
            n_epochs=self.config['n_epochs'],
            gamma=self.config['gamma'],
            gae_lambda=self.config['gae_lambda'],
            clip_range=self.config['clip_range'],
            ent_coef=self.config['ent_coef'],
            vf_coef=self.config['vf_coef'],
            max_grad_norm=self.config['max_grad_norm'],
            policy_kwargs=self.config['policy_kwargs'],
            verbose=1,
            tensorboard_log=None  # Disable tensorboard for demo
        )
        
        return model
    
    def train(self, 
              total_timesteps: int = None,
              save_best: bool = True,
              early_stopping: bool = True) -> Dict:
        """
        Train the RL policy.
        
        Returns:
            training_info: Dictionary with training results
        """
        print("Starting training...")
        start_time = time.time()
        
        # Create training environment
        self.env = self.create_environment()
        
        # Create evaluation environment
        eval_env = self.create_environment(seed=123)  # Different seed for eval
        
        # Create model
        self.model = self.create_model(self.env)
        
        # Setup callbacks
        callbacks = []
        
        if save_best:
            eval_callback = EvalCallback(
                eval_env,
                best_model_save_path=self.model_dir,
                log_path=self.log_dir,
                eval_freq=self.config['eval_freq'],
                n_eval_episodes=self.config['n_eval_episodes'],
                deterministic=True,
                render=False
            )
            callbacks.append(eval_callback)
        
        # Skip early stopping for demo to avoid callback issues
        # if early_stopping:
        #     stop_callback = StopTrainingOnRewardThreshold(
        #         reward_threshold=100.0,  # Adjust based on expected rewards
        #         verbose=1
        #     )
        #     callbacks.append(stop_callback)
        
        # Train model
        timesteps = total_timesteps or self.config['total_timesteps']
        
        try:
            self.model.learn(
                total_timesteps=timesteps,
                callback=callbacks,
                progress_bar=True
            )
        except KeyboardInterrupt:
            print("Training interrupted by user")
        
        # Save final model
        final_model_path = os.path.join(self.model_dir, "final_model")
        self.model.save(final_model_path)
        
        # Training summary
        training_time = time.time() - start_time
        training_info = {
            'total_timesteps': timesteps,
            'training_time': training_time,
            'final_model_path': final_model_path,
            'config': self.config
        }
        
        print(f"Training completed in {training_time:.2f} seconds")
        print(f"Final model saved to: {final_model_path}")
        
        return training_info
    
    def evaluate_model(self, 
                      model_path: str = None,
                      n_episodes: int = 10,
                      render: bool = False) -> Dict:
        """
        Evaluate trained model.
        
        Returns:
            evaluation_results: Dictionary with evaluation metrics
        """
        if model_path is None:
            model_path = os.path.join(self.model_dir, "final_model")
        
        # Load model
        model = PPO.load(model_path)
        
        # Create evaluation environment
        eval_env = self.create_environment(seed=456)
        
        # Run evaluation episodes
        episode_rewards = []
        episode_lengths = []
        kpi_history = []
        
        for episode in range(n_episodes):
            obs = eval_env.reset()
            done = False
            episode_reward = 0
            episode_length = 0
            
            while not done:
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, done, info = eval_env.step(action)
                episode_reward += reward
                episode_length += 1
                
                if render:
                    eval_env.render()
            
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            
            # Collect KPIs from last episode
            if episode == n_episodes - 1:
                kpi_history = eval_env.get_kpis()
        
        # Calculate statistics
        eval_results = {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_length': np.mean(episode_lengths),
            'std_length': np.std(episode_lengths),
            'episode_rewards': episode_rewards,
            'episode_lengths': episode_lengths,
            'final_kpis': kpi_history
        }
        
        print(f"Evaluation Results:")
        print(f"  Mean Reward: {eval_results['mean_reward']:.2f} ± {eval_results['std_reward']:.2f}")
        print(f"  Mean Episode Length: {eval_results['mean_length']:.2f} ± {eval_results['std_length']:.2f}")
        
        return eval_results
    
    def compare_with_baseline(self, 
                            model_path: str = None,
                            n_episodes: int = 5) -> Dict:
        """
        Compare RL policy with baseline fixed schedule.
        
        Returns:
            comparison_results: Dictionary with comparison metrics
        """
        if model_path is None:
            model_path = os.path.join(self.model_dir, "final_model")
        
        # Load RL model
        rl_model = PPO.load(model_path)
        
        # Run RL episodes
        print("Evaluating RL policy...")
        rl_results = self.evaluate_model(model_path, n_episodes)
        
        # Run baseline episodes
        print("Evaluating baseline policy...")
        baseline_results = self._evaluate_baseline(n_episodes)
        
        # Calculate improvements
        improvements = {}
        for metric in ['avg_wait', 'p90_wait', 'load_std']:
            if metric in rl_results['final_kpis'] and metric in baseline_results['final_kpis']:
                rl_val = rl_results['final_kpis'][metric]
                baseline_val = baseline_results['final_kpis'][metric]
                
                if baseline_val > 0:
                    improvement = ((baseline_val - rl_val) / baseline_val) * 100
                    improvements[f'{metric}_improvement'] = improvement
        
        comparison_results = {
            'rl_results': rl_results,
            'baseline_results': baseline_results,
            'improvements': improvements
        }
        
        print(f"Comparison Results:")
        for metric, improvement in improvements.items():
            print(f"  {metric}: {improvement:.1f}% improvement")
        
        return comparison_results
    
    def _evaluate_baseline(self, n_episodes: int) -> Dict:
        """Evaluate baseline fixed schedule policy."""
        env = self.create_environment(seed=789)
        
        episode_rewards = []
        episode_lengths = []
        kpi_history = []
        
        for episode in range(n_episodes):
            obs = env.reset()
            env.set_baseline_mode(True)  # Use baseline policy
            done = False
            episode_reward = 0
            episode_length = 0
            
            while not done:
                # Baseline: continue action for all buses
                action = np.zeros(env.num_buses, dtype=int)  # All CONTINUE actions
                obs, reward, done, info = env.step(action)
                episode_reward += reward
                episode_length += 1
            
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            
            if episode == n_episodes - 1:
                kpi_history = env.get_kpis()
        
        return {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'mean_length': np.mean(episode_lengths),
            'std_length': np.std(episode_lengths),
            'final_kpis': kpi_history
        }
    
    def save_config(self, config_path: str = None):
        """Save training configuration."""
        if config_path is None:
            config_path = os.path.join(self.model_dir, "config.json")
        
        with open(config_path, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_config(self, config_path: str):
        """Load training configuration."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)


def main():
    """Main training script."""
    # Initialize trainer
    trainer = BusRoutingTrainer()
    
    # Save configuration
    trainer.save_config()
    
    # Train model
    training_info = trainer.train()
    
    # Evaluate model
    eval_results = trainer.evaluate_model()
    
    # Compare with baseline
    comparison_results = trainer.compare_with_baseline()
    
    print("Training pipeline completed!")


if __name__ == "__main__":
    main()
