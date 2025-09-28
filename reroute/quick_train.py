
import os
import sys
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'env'))

from env.wrappers import BusDispatchEnv

def create_env():
    return BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        time_step=1.0,
        max_episode_time=60.0,
        seed=42
    )

# Create environment
env = make_vec_env(create_env, n_envs=1)

# Create simple PPO model
model = PPO(
    "MlpPolicy",
    env,
    learning_rate=3e-4,
    n_steps=512,
    batch_size=64,
    n_epochs=5,
    gamma=0.99,
    verbose=1,
    device="cpu"
)

print("Training for 10000 steps...")
model.learn(total_timesteps=10000, progress_bar=True)

# Save model
model.save("simple_bus_model")
print("✓ Model saved as simple_bus_model")

# Test the model
obs = env.reset()
for i in range(10):
    action, _ = model.predict(obs, deterministic=True)
    obs, reward, done, info = env.step(action)
    if done:
        obs = env.reset()
    print(f"Step {i}: Reward = {reward[0]:.2f}")

print("✓ Training completed!")
