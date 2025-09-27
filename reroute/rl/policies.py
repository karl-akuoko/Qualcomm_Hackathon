"""
Custom policy implementations for bus dispatching RL
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Any
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.utils import get_device

class BusDispatchFeaturesExtractor(BaseFeaturesExtractor):
    """Custom feature extractor for bus dispatch observations"""
    
    def __init__(self, observation_space, features_dim: int = 128):
        super().__init__(observation_space, features_dim)
        
        # Calculate input dimensions
        self.bus_features = 5  # x, y, load, is_moving, hold_time
        self.stop_features = 1  # queue_length
        self.num_buses = 6
        self.num_stops = 32
        
        # Bus feature processing
        self.bus_encoder = nn.Sequential(
            nn.Linear(self.bus_features, 32),
            nn.ReLU(),
            nn.Linear(32, 16)
        )
        
        # Stop feature processing
        self.stop_encoder = nn.Sequential(
            nn.Linear(self.stop_features, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        
        # Global context processing
        self.global_encoder = nn.Sequential(
            nn.Linear(16 * self.num_buses + 8 * self.num_stops, 64),
            nn.ReLU(),
            nn.Linear(64, features_dim)
        )
    
    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """Extract features from observations"""
        batch_size = observations.shape[0]
        
        # Split observations into bus and stop features
        bus_obs = observations[:, :self.num_buses * self.bus_features]
        stop_obs = observations[:, self.num_buses * self.bus_features:]
        
        # Reshape for processing
        bus_obs = bus_obs.view(batch_size, self.num_buses, self.bus_features)
        stop_obs = stop_obs.view(batch_size, self.num_stops, self.stop_features)
        
        # Process bus features
        bus_features = []
        for i in range(self.num_buses):
            bus_feat = self.bus_encoder(bus_obs[:, i, :])
            bus_features.append(bus_feat)
        
        bus_features = torch.cat(bus_features, dim=1)  # [batch_size, num_buses * 16]
        
        # Process stop features
        stop_features = []
        for i in range(self.num_stops):
            stop_feat = self.stop_encoder(stop_obs[:, i, :])
            stop_features.append(stop_feat)
        
        stop_features = torch.cat(stop_features, dim=1)  # [batch_size, num_stops * 8]
        
        # Combine and process globally
        combined = torch.cat([bus_features, stop_features], dim=1)
        features = self.global_encoder(combined)
        
        return features

class BusDispatchPolicy(ActorCriticPolicy):
    """Custom policy for bus dispatching with domain-specific architecture"""
    
    def __init__(self, observation_space, action_space, lr_schedule, **kwargs):
        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            features_extractor_class=BusDispatchFeaturesExtractor,
            features_extractor_kwargs={"features_dim": 128},
            **kwargs
        )
    
    def forward(self, obs: torch.Tensor, deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass with custom logic"""
        return super().forward(obs, deterministic)

class MultiHeadPolicy(nn.Module):
    """Multi-head policy for different bus types or scenarios"""
    
    def __init__(self, input_dim: int, num_heads: int = 3, actions_per_head: int = 4):
        super().__init__()
        self.num_heads = num_heads
        self.actions_per_head = actions_per_head
        
        # Shared feature extractor
        self.shared_encoder = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64)
        )
        
        # Separate heads for different scenarios
        self.heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, actions_per_head)
            ) for _ in range(num_heads)
        ])
        
        # Head selection network
        self.head_selector = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, num_heads)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through multi-head architecture"""
        # Extract shared features
        shared_features = self.shared_encoder(x)
        
        # Select appropriate head based on context
        head_weights = torch.softmax(self.head_selector(shared_features), dim=-1)
        
        # Get outputs from all heads
        head_outputs = []
        for head in self.heads:
            head_outputs.append(head(shared_features))
        
        # Weighted combination of head outputs
        weighted_output = torch.zeros_like(head_outputs[0])
        for i, (head_output, weight) in enumerate(zip(head_outputs, head_weights.T)):
            weighted_output += head_output * weight.unsqueeze(-1)
        
        return weighted_output

class AttentionPolicy(nn.Module):
    """Attention-based policy for bus dispatching"""
    
    def __init__(self, input_dim: int, num_buses: int = 6, num_actions: int = 4):
        super().__init__()
        self.num_buses = num_buses
        self.num_actions = num_actions
        
        # Feature dimensions
        self.bus_dim = 5
        self.stop_dim = 1
        self.num_stops = 32
        
        # Bus and stop encoders
        self.bus_encoder = nn.Linear(self.bus_dim, 32)
        self.stop_encoder = nn.Linear(self.stop_dim, 16)
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(embed_dim=32, num_heads=4, batch_first=True)
        
        # Policy network
        self.policy_net = nn.Sequential(
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, num_actions)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with attention mechanism"""
        batch_size = x.shape[0]
        
        # Split and encode bus and stop features
        bus_features = x[:, :self.num_buses * self.bus_dim]
        stop_features = x[:, self.num_buses * self.bus_dim:]
        
        # Reshape for attention
        bus_features = bus_features.view(batch_size, self.num_buses, self.bus_dim)
        bus_encoded = self.bus_encoder(bus_features)  # [batch_size, num_buses, 32]
        
        stop_features = stop_features.view(batch_size, self.num_stops, self.stop_dim)
        stop_encoded = self.stop_encoder(stop_features)  # [batch_size, num_stops, 16]
        
        # Pad stop features to match bus features
        stop_padded = torch.zeros(batch_size, self.num_stops, 32)
        stop_padded[:, :, :16] = stop_encoded
        
        # Combine bus and stop features
        all_features = torch.cat([bus_encoded, stop_padded], dim=1)  # [batch_size, num_buses + num_stops, 32]
        
        # Apply attention
        attended_features, _ = self.attention(all_features, all_features, all_features)
        
        # Extract bus-specific features
        bus_attended = attended_features[:, :self.num_buses, :]  # [batch_size, num_buses, 32]
        
        # Generate actions for each bus
        actions = []
        for i in range(self.num_buses):
            bus_feat = bus_attended[:, i, :]  # [batch_size, 32]
            bus_action = self.policy_net(bus_feat)  # [batch_size, num_actions]
            actions.append(bus_action)
        
        # Stack actions
        actions = torch.stack(actions, dim=1)  # [batch_size, num_buses, num_actions]
        
        return actions

class CurriculumPolicy:
    """Curriculum learning wrapper for policy training"""
    
    def __init__(self, base_policy, curriculum_schedule: Dict[str, Any]):
        self.base_policy = base_policy
        self.curriculum_schedule = curriculum_schedule
        self.current_phase = 0
        self.training_steps = 0
    
    def update_curriculum(self, training_steps: int):
        """Update curriculum based on training progress"""
        self.training_steps = training_steps
        
        # Find current phase
        for phase, schedule in self.curriculum_schedule.items():
            if schedule['start'] <= training_steps <= schedule['end']:
                self.current_phase = int(phase)
                break
    
    def get_curriculum_params(self) -> Dict[str, Any]:
        """Get current curriculum parameters"""
        if str(self.current_phase) in self.curriculum_schedule:
            return self.curriculum_schedule[str(self.current_phase)]
        return {}
    
    def apply_curriculum(self, env):
        """Apply curriculum modifications to environment"""
        params = self.get_curriculum_params()
        
        # Example curriculum modifications
        if 'traffic_level' in params:
            # Gradually increase traffic complexity
            env.traffic_model.set_traffic_level(params['traffic_level'])
        
        if 'demand_multiplier' in params:
            # Gradually increase demand
            env.rider_generator.set_demand_multiplier(params['demand_multiplier'])
        
        if 'disruption_frequency' in params:
            # Gradually introduce disruptions
            env.set_disruption_frequency(params['disruption_frequency'])

def create_curriculum_schedule() -> Dict[str, Any]:
    """Create curriculum learning schedule"""
    return {
        '0': {  # Phase 0: Basic operation
            'start': 0,
            'end': 10000,
            'traffic_level': 0.1,
            'demand_multiplier': 0.5,
            'disruption_frequency': 0.0
        },
        '1': {  # Phase 1: Light traffic
            'start': 10000,
            'end': 30000,
            'traffic_level': 0.3,
            'demand_multiplier': 0.7,
            'disruption_frequency': 0.1
        },
        '2': {  # Phase 2: Moderate traffic
            'start': 30000,
            'end': 60000,
            'traffic_level': 0.6,
            'demand_multiplier': 1.0,
            'disruption_frequency': 0.2
        },
        '3': {  # Phase 3: Heavy traffic with disruptions
            'start': 60000,
            'end': 100000,
            'traffic_level': 1.0,
            'demand_multiplier': 1.5,
            'disruption_frequency': 0.3
        }
    }
