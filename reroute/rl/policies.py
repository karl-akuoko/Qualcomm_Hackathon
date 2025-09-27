"""
Custom policy networks for the bus routing RL agent.
Includes specialized architectures for multi-bus coordination.
"""

import torch
import torch.nn as nn
import numpy as np
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from gymnasium import spaces
from typing import Dict, List, Tuple, Type


class BusRoutingFeaturesExtractor(BaseFeaturesExtractor):
    """
    Custom feature extractor for bus routing environment.
    Processes bus states, stop states, and global information.
    """
    
    def __init__(self, observation_space: spaces.Box, features_dim: int = 256):
        super().__init__(observation_space, features_dim)
        
        # Calculate input dimensions
        self.num_buses = 6  # Fixed for this environment
        self.num_stops = 35  # Fixed for this environment
        
        bus_state_dim = 6
        stop_state_dim = 3
        global_state_dim = 2
        
        bus_input_dim = self.num_buses * bus_state_dim
        stop_input_dim = self.num_stops * stop_state_dim
        
        # Bus feature processing
        self.bus_encoder = nn.Sequential(
            nn.Linear(bus_state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32)
        )
        
        # Stop feature processing
        self.stop_encoder = nn.Sequential(
            nn.Linear(stop_state_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16)
        )
        
        # Global feature processing
        self.global_encoder = nn.Sequential(
            nn.Linear(global_state_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        
        # Combined feature processing
        combined_dim = self.num_buses * 32 + self.num_stops * 16 + 8
        self.combined_encoder = nn.Sequential(
            nn.Linear(combined_dim, 512),
            nn.ReLU(),
            nn.Linear(512, features_dim),
            nn.ReLU()
        )
        
    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """
        Extract features from observations.
        
        Args:
            observations: Shape (batch_size, obs_dim)
        
        Returns:
            features: Shape (batch_size, features_dim)
        """
        batch_size = observations.shape[0]
        
        # Split observations into components
        bus_state_dim = 6
        stop_state_dim = 3
        
        bus_obs = observations[:, :self.num_buses * bus_state_dim]
        stop_obs = observations[:, self.num_buses * bus_state_dim:self.num_buses * bus_state_dim + self.num_stops * stop_state_dim]
        global_obs = observations[:, -2:]
        
        # Process bus features
        bus_obs_reshaped = bus_obs.view(batch_size, self.num_buses, bus_state_dim)
        bus_features = self.bus_encoder(bus_obs_reshaped)
        bus_features_flat = bus_features.view(batch_size, -1)
        
        # Process stop features
        stop_obs_reshaped = stop_obs.view(batch_size, self.num_stops, stop_state_dim)
        stop_features = self.stop_encoder(stop_obs_reshaped)
        stop_features_flat = stop_features.view(batch_size, -1)
        
        # Process global features
        global_features = self.global_encoder(global_obs)
        
        # Combine all features
        combined_features = torch.cat([
            bus_features_flat,
            stop_features_flat,
            global_features
        ], dim=1)
        
        # Final feature extraction
        features = self.combined_encoder(combined_features)
        
        return features


class MultiBusPolicy(nn.Module):
    """
    Policy network specifically designed for multi-bus coordination.
    Uses attention mechanisms to coordinate between buses.
    """
    
    def __init__(self, 
                 obs_dim: int,
                 action_dim: int,
                 num_buses: int = 6,
                 hidden_dim: int = 256):
        super().__init__()
        
        self.num_buses = num_buses
        self.action_dim = action_dim
        
        # Feature extractor
        self.feature_extractor = BusRoutingFeaturesExtractor(
            spaces.Box(low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32),
            features_dim=hidden_dim
        )
        
        # Attention mechanism for bus coordination
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=8,
            batch_first=True
        )
        
        # Individual bus policy heads
        self.bus_policies = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, action_dim)
            )
            for _ in range(num_buses)
        ])
        
        # Value function
        self.value_net = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through policy network.
        
        Args:
            obs: Observations (batch_size, obs_dim)
        
        Returns:
            actions: Action logits (batch_size, num_buses, action_dim)
            value: Value estimate (batch_size, 1)
        """
        batch_size = obs.shape[0]
        
        # Extract features
        features = self.feature_extractor(obs)  # (batch_size, hidden_dim)
        
        # Apply attention (self-attention for coordination)
        features_expanded = features.unsqueeze(1).repeat(1, self.num_buses, 1)
        attended_features, _ = self.attention(features_expanded, features_expanded, features_expanded)
        
        # Get individual bus actions
        actions = []
        for i in range(self.num_buses):
            bus_features = attended_features[:, i, :]
            bus_actions = self.bus_policies[i](bus_features)
            actions.append(bus_actions)
        
        actions = torch.stack(actions, dim=1)  # (batch_size, num_buses, action_dim)
        
        # Get value estimate
        value = self.value_net(features)
        
        return actions, value


class HierarchicalPolicy(nn.Module):
    """
    Hierarchical policy with high-level coordination and low-level execution.
    """
    
    def __init__(self,
                 obs_dim: int,
                 action_dim: int,
                 num_buses: int = 6,
                 coordination_dim: int = 64):
        super().__init__()
        
        self.num_buses = num_buses
        self.action_dim = action_dim
        self.coordination_dim = coordination_dim
        
        # High-level coordinator
        self.coordinator = nn.Sequential(
            nn.Linear(obs_dim, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, coordination_dim)
        )
        
        # Low-level executors for each bus
        self.executors = nn.ModuleList([
            nn.Sequential(
                nn.Linear(obs_dim + coordination_dim, 256),
                nn.ReLU(),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, action_dim)
            )
            for _ in range(num_buses)
        ])
        
        # Value function
        self.value_net = nn.Sequential(
            nn.Linear(obs_dim + coordination_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through hierarchical policy.
        
        Args:
            obs: Observations (batch_size, obs_dim)
        
        Returns:
            actions: Action logits (batch_size, num_buses, action_dim)
            value: Value estimate (batch_size, 1)
        """
        batch_size = obs.shape[0]
        
        # High-level coordination
        coordination = self.coordinator(obs)  # (batch_size, coordination_dim)
        
        # Combine observation with coordination signal
        obs_coord = torch.cat([obs, coordination], dim=1)
        
        # Low-level execution
        actions = []
        for i in range(self.num_buses):
            bus_actions = self.executors[i](obs_coord)
            actions.append(bus_actions)
        
        actions = torch.stack(actions, dim=1)  # (batch_size, num_buses, action_dim)
        
        # Value estimate
        value = self.value_net(obs_coord)
        
        return actions, value


def get_policy_kwargs(policy_type: str = "default") -> Dict:
    """
    Get policy kwargs for different policy types.
    
    Args:
        policy_type: Type of policy ("default", "attention", "hierarchical")
    
    Returns:
        policy_kwargs: Dictionary with policy configuration
    """
    if policy_type == "attention":
        return {
            'features_extractor_class': BusRoutingFeaturesExtractor,
            'features_extractor_kwargs': {'features_dim': 256}
        }
    elif policy_type == "hierarchical":
        return {
            'features_extractor_class': BusRoutingFeaturesExtractor,
            'features_extractor_kwargs': {'features_dim': 256},
            'net_arch': [256, 128, 64]
        }
    else:  # default
        return {
            'net_arch': [256, 256, 128],
            'activation_fn': torch.nn.ReLU
        }


# Example usage and testing
if __name__ == "__main__":
    # Test feature extractor
    obs_space = spaces.Box(low=-np.inf, high=np.inf, shape=(300,), dtype=np.float32)
    feature_extractor = BusRoutingFeaturesExtractor(obs_space, 256)
    
    # Test forward pass
    batch_size = 32
    obs = torch.randn(batch_size, 300)
    features = feature_extractor(obs)
    print(f"Feature extractor output shape: {features.shape}")
    
    # Test multi-bus policy
    policy = MultiBusPolicy(obs_dim=300, action_dim=4, num_buses=6)
    actions, value = policy(obs)
    print(f"Multi-bus policy actions shape: {actions.shape}")
    print(f"Multi-bus policy value shape: {value.shape}")
