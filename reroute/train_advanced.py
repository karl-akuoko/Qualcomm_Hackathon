#!/usr/bin/env python3
"""
Advanced training with multiple model types and better optimization
"""

import os
import sys
import numpy as np
import torch
import torch.nn as nn
from stable_baselines3 import PPO, A2C, DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
import gymnasium as gym
from typing import Dict, List, Any

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

class CustomPolicy(nn.Module):
    """Custom neural network policy for bus dispatching"""
    
    def __init__(self, observation_space, action_space, lr_schedule=None):
        super().__init__()
        
        self.observation_space = observation_space
        self.action_space = action_space
        
        # Feature extraction layers
        self.feature_extractor = nn.Sequential(
            nn.Linear(observation_space.shape[0], 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU()
        )
        
        # Value network
        self.value_net = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # Action network (for each bus)
        self.action_net = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, action_space.n)
        )
        
    def forward(self, obs):
        features = self.feature_extractor(obs)
        value = self.value_net(features)
        action_logits = self.action_net(features)
        return action_logits, value

class TrainingCallback(BaseCallback):
    """Advanced training callback with better monitoring"""
    
    def __init__(self, check_freq: int = 1000, verbose: int = 1):
        super().__init__(verbose)
        self.check_freq = check_freq
        self.best_mean_reward = -np.inf
        self.episode_rewards = []
        self.episode_lengths = []
        
    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            if len(self.model.ep_info_buffer) > 0:
                # Get training stats
                mean_reward = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
                mean_length = np.mean([ep_info["l"] for ep_info in self.model.ep_info_buffer])
                
                self.episode_rewards.append(mean_reward)
                self.episode_lengths.append(mean_length)
                
                if self.verbose > 0:
                    print(f"Steps: {self.n_calls}")
                    print(f"Mean reward: {mean_reward:.2f}")
                    print(f"Mean episode length: {mean_length:.0f}")
                    
                    # Check for improvement
                    if mean_reward > self.best_mean_reward:
                        self.best_mean_reward = mean_reward
                        print(f"🎉 New best reward: {self.best_mean_reward:.2f}")
                        self.model.save("best_bus_model")
                    else:
                        print(f"Current best: {self.best_mean_reward:.2f}")
                    
                    print("---")
        
        return True

def create_training_env(seed: int = 42):
    """Create training environment with curriculum learning"""
    
    def _init():
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=1.0,  # 1 minute steps
            max_episode_time=120.0,  # 2 hour episodes
            seed=seed
        )
        return env
    
    return _init

def train_multiple_models():
    """Train multiple model types and compare performance"""
    
    print("=" * 60)
    print("TRAINING MULTIPLE BUS DISPATCH MODELS")
    print("=" * 60)
    
    # Create vectorized environment
    env = make_vec_env(create_training_env(42), n_envs=1)
    
    models = {}
    results = {}
    
    # Model 1: PPO with custom policy
    print("\n🤖 Training PPO with custom policy...")
    try:
        ppo_model = PPO(
            "MlpPolicy",
            env,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,
            vf_coef=0.5,
            max_grad_norm=0.5,
            verbose=1,
            device="cpu",
            seed=42,
            tensorboard_log="./ppo_bus_tensorboard/"
        )
        
        callback = TrainingCallback(check_freq=1000, verbose=1)
        ppo_model.learn(total_timesteps=20000, callback=callback, progress_bar=True)
        ppo_model.save("ppo_bus_model")
        models["PPO"] = ppo_model
        results["PPO"] = callback.best_mean_reward
        print(f"✅ PPO trained - Best reward: {callback.best_mean_reward:.2f}")
        
    except Exception as e:
        print(f"❌ PPO training failed: {e}")
    
    # Model 2: A2C
    print("\n🤖 Training A2C...")
    try:
        a2c_model = A2C(
            "MlpPolicy",
            env,
            learning_rate=7e-4,
            n_steps=5,
            gamma=0.99,
            gae_lambda=1.0,
            ent_coef=0.0,
            vf_coef=0.25,
            max_grad_norm=0.5,
            verbose=1,
            device="cpu",
            seed=42
        )
        
        callback = TrainingCallback(check_freq=1000, verbose=1)
        a2c_model.learn(total_timesteps=20000, callback=callback, progress_bar=True)
        a2c_model.save("a2c_bus_model")
        models["A2C"] = a2c_model
        results["A2C"] = callback.best_mean_reward
        print(f"✅ A2C trained - Best reward: {callback.best_mean_reward:.2f}")
        
    except Exception as e:
        print(f"❌ A2C training failed: {e}")
    
    # Model 3: DQN
    print("\n🤖 Training DQN...")
    try:
        dqn_model = DQN(
            "MlpPolicy",
            env,
            learning_rate=1e-4,
            buffer_size=50000,
            learning_starts=1000,
            batch_size=32,
            tau=1.0,
            gamma=0.99,
            train_freq=4,
            gradient_steps=1,
            target_update_interval=1000,
            exploration_fraction=0.1,
            exploration_initial_eps=1.0,
            exploration_final_eps=0.05,
            max_grad_norm=10,
            verbose=1,
            device="cpu",
            seed=42
        )
        
        callback = TrainingCallback(check_freq=1000, verbose=1)
        dqn_model.learn(total_timesteps=20000, callback=callback, progress_bar=True)
        dqn_model.save("dqn_bus_model")
        models["DQN"] = dqn_model
        results["DQN"] = callback.best_mean_reward
        print(f"✅ DQN trained - Best reward: {callback.best_mean_reward:.2f}")
        
    except Exception as e:
        print(f"❌ DQN training failed: {e}")
    
    # Select best model
    if results:
        best_model_name = max(results, key=results.get)
        best_model = models[best_model_name]
        best_reward = results[best_model_name]
        
        print(f"\n🏆 Best model: {best_model_name} (reward: {best_reward:.2f})")
        
        # Save best model
        best_model.save("best_bus_model")
        print("✅ Best model saved as 'best_bus_model'")
        
        return best_model, best_model_name
    else:
        print("❌ No models trained successfully")
        return None, None

def evaluate_model(model, model_name: str, n_episodes: int = 5):
    """Evaluate trained model"""
    
    print(f"\n📊 Evaluating {model_name}...")
    
    # Create evaluation environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=60.0,
        seed=42
    )
    
    episode_rewards = []
    episode_improvements = []
    
    for episode in range(n_episodes):
        obs, info = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            episode_reward += reward
            
            if done or truncated:
                break
        
        episode_rewards.append(episode_reward)
        
        # Get final improvements
        if hasattr(env, '_get_info'):
            info = env._get_info()
            if 'improvements' in info:
                episode_improvements.append(info['improvements'])
        
        print(f"Episode {episode + 1}: Reward = {episode_reward:.2f}")
    
    # Print results
    print(f"\n📈 {model_name} Evaluation Results:")
    print(f"Mean reward: {np.mean(episode_rewards):.2f} ± {np.std(episode_rewards):.2f}")
    
    if episode_improvements:
        avg_improvements = np.mean([imp.get('avg_wait', 0) for imp in episode_improvements])
        print(f"Average wait improvement: {avg_improvements:.1%}")
    
    return episode_rewards

def main():
    """Main training function"""
    
    print("🚀 Starting advanced bus dispatch training...")
    
    # Train multiple models
    best_model, best_name = train_multiple_models()
    
    if best_model is not None:
        # Evaluate best model
        evaluate_model(best_model, best_name)
        
        print(f"\n✅ Training completed! Best model: {best_name}")
        print("✅ Model saved as 'best_bus_model'")
        print("✅ Ready for deployment!")
    else:
        print("\n❌ Training failed!")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Training pipeline completed successfully!")
    else:
        print("\n💥 Training pipeline failed!")
        sys.exit(1)
