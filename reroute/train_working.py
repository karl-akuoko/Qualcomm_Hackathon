#!/usr/bin/env python3
"""
Working training script with proper imports
"""

import os
import sys
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
env_dir = os.path.join(current_dir, 'env')
rl_dir = os.path.join(current_dir, 'rl')

sys.path.insert(0, current_dir)
sys.path.insert(0, env_dir)
sys.path.insert(0, rl_dir)

# Now import the environment
from env.wrappers import BusDispatchEnv

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
                    print("---")
                
                # Save best model
                if mean_reward > self.best_mean_reward:
                    self.best_mean_reward = mean_reward
                    if self.verbose > 0:
                        print(f"New best mean reward: {self.best_mean_reward:.2f}")
                    self.model.save(os.path.join(self.model.logger.dir, "best_model"))
        
        return True

def create_training_env(seed: int = 42):
    """Create training environment"""
    
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
    total_timesteps: int = 50000,  # Reduced for faster training
    learning_rate: float = 3e-4,
    n_steps: int = 1024,  # Reduced for faster training
    batch_size: int = 64,
    n_epochs: int = 10,
    gamma: float = 0.99,
    seed: int = 42,
    device: str = "auto"
):
    """Train PPO policy for bus dispatching"""
    
    print("=" * 50)
    print("TRAINING PPO POLICY FOR BUS DISPATCHING")
    print("=" * 50)
    
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

def export_to_onnx(model_path: str, onnx_path: str = "ppo_bus_policy.onnx"):
    """Export trained model to ONNX format"""
    
    print("=" * 50)
    print("EXPORTING MODEL TO ONNX")
    print("=" * 50)
    
    try:
        import torch.onnx
        import onnx
        import onnxruntime as ort
        
        print(f"Loading model from {model_path}")
        model = PPO.load(model_path)
        
        # Create dummy environment
        env = BusDispatchEnv(seed=42)
        obs = env.reset()
        
        # Get policy network
        policy_net = model.policy.mlp_extractor
        action_net = model.policy.action_net
        
        # Create wrapper for ONNX export
        class ONNXPolicyWrapper(torch.nn.Module):
            def __init__(self, mlp_extractor, action_net):
                super().__init__()
                self.mlp_extractor = mlp_extractor
                self.action_net = action_net
                
            def forward(self, observations):
                features = self.mlp_extractor.forward_actor(observations)
                action_logits = self.action_net(features)
                action_probs = torch.softmax(action_logits, dim=-1)
                return action_probs, action_logits
        
        onnx_model = ONNXPolicyWrapper(policy_net, action_net)
        onnx_model.eval()
        
        # Create dummy input
        dummy_input = torch.randn(1, *obs.shape, dtype=torch.float32)
        
        print("Exporting to ONNX...")
        torch.onnx.export(
            onnx_model,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['observations'],
            output_names=['action_probs', 'action_logits'],
            dynamic_axes={
                'observations': {0: 'batch_size'},
                'action_probs': {0: 'batch_size'},
                'action_logits': {0: 'batch_size'}
            }
        )
        
        print(f"✓ Model exported to {onnx_path}")
        
        # Verify ONNX model
        onnx_model_loaded = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model_loaded)
        print("✓ ONNX model is valid")
        
        return onnx_path
        
    except ImportError as e:
        print(f"✗ ONNX dependencies not available: {e}")
        print("Install with: pip install onnx onnxruntime")
        return None
    except Exception as e:
        print(f"✗ ONNX export failed: {e}")
        return None

def main():
    """Main training function"""
    
    print("Starting complete training pipeline...")
    
    # Step 1: Train the model
    print("\n1. Training PPO model...")
    model = train_ppo_policy(
        total_timesteps=50000,  # Reduced for demo
        learning_rate=3e-4,
        seed=42
    )
    
    # Step 2: Export to ONNX
    print("\n2. Exporting to ONNX...")
    onnx_path = export_to_onnx("ppo_bus_final")
    
    if onnx_path:
        print(f"✓ Complete! ONNX model ready at {onnx_path}")
        print("✓ Server can now use RL mode")
    else:
        print("✗ ONNX export failed, but PPO model is available")
        print("✓ Server will run in static mode only")
    
    print("\n" + "=" * 50)
    print("TRAINING COMPLETE!")
    print("=" * 50)

if __name__ == "__main__":
    main()
