import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
import torch
import sys
sys.path.append('../env')
from wrappers import BusDispatchEnv

class TrainingCallback(BaseCallback):
    """Custom callback to track training progress"""
    
    def __init__(self, check_freq: int = 1000, verbose: int = 1):
        super().__init__(verbose)
        self.check_freq = check_freq
        self.best_mean_reward = -np.inf
        
    def _on_step(self) -> bool:
        if self.n_calls % self.check_freq == 0:
            # Get training stats
            if len(self.model.ep_info_buffer) > 0:
                mean_reward = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
                mean_length = np.mean([ep_info["l"] for ep_info in self.model.ep_info_buffer])
                
                if self.verbose > 0:
                    print(f"Steps: {self.n_calls}")
                    print(f"Mean reward: {mean_reward:.2f}")
                    print(f"Mean episode length: {mean_length:.0f}")
                    
                    # Get latest environment info if available
                    if hasattr(self.locals, 'infos') and len(self.locals['infos']) > 0:
                        info = self.locals['infos'][0]
                        if 'improvements' in info:
                            print(f"Avg wait improvement: {info['improvements']['avg_wait']:.1%}")
                            print(f"Overcrowd improvement: {info['improvements']['overcrowd']:.1%}")
                    print("---")
                
                # Save best model
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    if self.verbose > 0:
                        print(f"New best mean reward: {self.best_mean_reward:.2f}")
                    self.model.save(os.path.join(self.model.logger.dir, "best_model"))
        
        return True

def create_training_env(seed: int = 42):
    """Create training environment with curriculum"""
    
    def _init():
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,  # 30 seconds
            max_episode_time=60.0,  # 1 hour episodes for training
            seed=seed
        )
        return env
    
    return _init

def train_ppo_policy(
    total_timesteps: int = 100000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    gamma: float = 0.99,
    seed: int = 42,
    device: str = "auto"
):
    """Train PPO policy for bus dispatching"""
    
    print("Creating training environment...")
    
    # Create vectorized environment
    env = make_vec_env(create_training_env(seed), n_envs=1)
    
    print("Initializing PPO agent...")
    
    # PPO configuration
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=gamma,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        device=device,
        seed=seed,
        tensorboard_log="./ppo_bus_tensorboard/"
    )
    
    # Create callback
    callback = TrainingCallback(check_freq=1000, verbose=1)
    
    print("Starting training...")
    print(f"Total timesteps: {total_timesteps}")
    print(f"Learning rate: {learning_rate}")
    print(f"Device: {model.device}")
    print("=" * 50)
    
    # Train the model
    model.learn(
        total_timesteps=total_timesteps,
        callback=callback,
        progress_bar=True
    )
    
    print("Training completed!")
    
    # Save final model
    model_path = "ppo_bus_final"
    model.save(model_path)
    print(f"Model saved to {model_path}")
    
    return model

def evaluate_policy(model_path: str, n_episodes: int = 10, render: bool = False):
    """Evaluate trained policy"""
    
    print(f"Loading model from {model_path}")
    
    # Create evaluation environment
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=0.5,
        max_episode_time=120.0,  # Longer episodes for evaluation
        seed=42
    )
    
    # Load model
    model = PPO.load(model_path)
    
    episode_rewards = []
    episode_improvements = {"avg_wait": [], "overcrowd": []}
    
    print(f"Evaluating for {n_episodes} episodes...")
    
    for episode in range(n_episodes):
        obs = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            episode_reward += reward
            
            if render:
                env.render()
        
        episode_rewards.append(episode_reward)
        
        # Collect final improvements
        if 'improvements' in info:
            episode_improvements["avg_wait"].append(info['improvements']['avg_wait'])
            episode_improvements["overcrowd"].append(info['improvements']['overcrowd'])
        
        print(f"Episode {episode + 1}: Reward = {episode_reward:.2f}")
        if 'improvements' in info:
            print(f"  Avg wait improvement: {info['improvements']['avg_wait']:.1%}")
            print(f"  Overcrowd improvement: {info['improvements']['overcrowd']:.1%}")
    
    # Print summary statistics
    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Mean reward: {np.mean(episode_rewards):.2f} ± {np.std(episode_rewards):.2f}")
    
    if episode_improvements["avg_wait"]:
        print(f"Mean avg wait improvement: {np.mean(episode_improvements['avg_wait']):.1%}")
        print(f"Mean overcrowd improvement: {np.mean(episode_improvements['overcrowd']):.1%}")
    
    return {
        "episode_rewards": episode_rewards,
        "improvements": episode_improvements
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train PPO policy for bus dispatching")
    parser.add_argument("--mode", type=str, choices=["train", "eval"], default="train",
                       help="Mode: train or evaluate")
    parser.add_argument("--timesteps", type=int, default=100000,
                       help="Total training timesteps")
    parser.add_argument("--lr", type=float, default=3e-4,
                       help="Learning rate")
    parser.add_argument("--model", type=str, default="ppo_bus_final",
                       help="Model path for evaluation")
    parser.add_argument("--episodes", type=int, default=10,
                       help="Number of evaluation episodes")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed")
    parser.add_argument("--render", action="store_true",
                       help="Render during evaluation")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        print("Starting PPO training for bus dispatching...")
        model = train_ppo_policy(
            total_timesteps=args.timesteps,
            learning_rate=args.lr,
            seed=args.seed
        )
        
        print("Training completed! Running quick evaluation...")
        evaluate_policy("ppo_bus_final", n_episodes=3)
        
    elif args.mode == "eval":
        print("Evaluating trained policy...")
        evaluate_policy(args.model, n_episodes=args.episodes, render=args.render)