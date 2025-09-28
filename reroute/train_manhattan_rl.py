#!/usr/bin/env python3
"""
Train Manhattan Bus Dispatch RL Model
Train a reinforcement learning model for dynamic bus routing in Manhattan
"""

import sys
import os
import numpy as np
import random
from typing import Dict, List, Any, Tuple
import json

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'env'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'rl'))

from manhattan_data_parser import ManhattanDataParser, ManhattanStop, ManhattanRoute

class ManhattanRLEnvironment:
    """Manhattan-specific RL environment for bus dispatch"""
    
    def __init__(self):
        self.parser = ManhattanDataParser()
        self.stops = {}
        self.routes = {}
        self.buses = {}
        self.passengers = {}
        self.simulation_time = 0
        
        # Load Manhattan data
        self._load_manhattan_data()
        self._initialize_system()
        
        # RL parameters
        self.action_space_size = 4  # 0: continue, 1: go to high demand, 2: skip low demand, 3: hold
        self.observation_space_size = 50  # State representation size
        
    def _load_manhattan_data(self):
        """Load real Manhattan bus data"""
        print("🗽 Loading Manhattan bus data for RL training...")
        
        self.stops = self.parser.load_manhattan_stops()
        self.routes = self.parser.create_manhattan_routes()
        
        print(f"✅ Loaded {len(self.stops)} stops and {len(self.routes)} routes")
    
    def _initialize_system(self):
        """Initialize the Manhattan bus system for RL training"""
        print("🚌 Initializing Manhattan bus system for RL...")
        
        # Create buses for each route
        self.buses = {}
        bus_id = 0
        
        for route_id, route in self.routes.items():
            # Create 2-3 buses per route
            num_buses = 2 if "SBS" in route_id else 3
            
            for i in range(num_buses):
                bus = {
                    "id": bus_id,
                    "route_id": route_id,
                    "route_name": route.route_name,
                    "current_stop": route.stops[0] if route.stops else None,
                    "next_stop_index": 0,
                    "x": self.stops[route.stops[0]].x if route.stops else 0,
                    "y": self.stops[route.stops[0]].y if route.stops else 0,
                    "load": 0,
                    "capacity": 40,
                    "color": route.color,
                    "direction": route.direction,
                    "speed": 1.0,
                    "status": "moving",
                    "passengers": []
                }
                self.buses[bus_id] = bus
                bus_id += 1
        
        # Initialize passenger queues at stops
        self.passengers = {}
        for stop_id, stop in self.stops.items():
            self.passengers[stop_id] = {
                "waiting": [],
                "total_wait_time": 0.0,
                "queue_length": 0
            }
        
        print(f"✅ Initialized {len(self.buses)} buses on {len(self.routes)} routes")
    
    def get_manhattan_demand(self, stop_id: str, hour: int) -> float:
        """Get realistic demand for Manhattan stops"""
        stop = self.stops[stop_id]
        
        # Base demand by location
        base_demand = 1.0
        
        # Major transfer points have higher demand
        if "TRANS" in stop_id:
            base_demand = 2.5
        elif any(route in stop.routes for route in ["M1", "M2", "M3", "M4"]):  # 5th Ave
            base_demand = 1.8
        elif any(route in stop.routes for route in ["M5", "M7", "M104"]):  # Broadway
            base_demand = 1.6
        elif "M14" in stop.routes[0] if stop.routes else False:  # 14th St
            base_demand = 1.4
        
        # Time-based demand patterns
        if 7 <= hour <= 9:  # Morning rush
            time_factor = 1.5
        elif 17 <= hour <= 19:  # Evening rush
            time_factor = 1.3
        elif 10 <= hour <= 16:  # Midday
            time_factor = 0.8
        else:  # Night
            time_factor = 0.3
        
        return base_demand * time_factor
    
    def generate_passengers(self):
        """Generate passengers based on Manhattan demand patterns"""
        current_hour = (self.simulation_time // 3600) % 24
        
        for stop_id, stop in self.stops.items():
            demand = self.get_manhattan_demand(stop_id, current_hour)
            
            # Generate passengers based on demand
            if random.random() < demand * 0.1:  # 10% chance per time step
                # Create passenger with destination
                destination_stops = [s for s in self.stops.keys() if s != stop_id]
                destination = random.choice(destination_stops)
                
                passenger = {
                    "id": f"p_{len(self.passengers[stop_id]['waiting'])}",
                    "destination": destination,
                    "arrival_time": self.simulation_time,
                    "wait_time": 0
                }
                
                self.passengers[stop_id]["waiting"].append(passenger)
                self.passengers[stop_id]["queue_length"] = len(self.passengers[stop_id]["waiting"])
    
    def get_observation(self) -> np.ndarray:
        """Get current observation for RL agent"""
        obs = []
        
        # Bus states (position, load, status)
        for bus in self.buses.values():
            obs.extend([bus["x"], bus["y"], bus["load"], 1 if bus["status"] == "moving" else 0])
        
        # Stop states (queue length, demand)
        for stop_id, stop in self.stops.items():
            obs.extend([self.passengers[stop_id]["queue_length"], 
                       self.get_manhattan_demand(stop_id, (self.simulation_time // 3600) % 24)])
        
        # Pad to fixed size
        while len(obs) < self.observation_space_size:
            obs.append(0.0)
        
        return np.array(obs[:self.observation_space_size], dtype=np.float32)
    
    def apply_action(self, bus_id: int, action: int):
        """Apply RL action to a bus"""
        bus = self.buses[bus_id]
        
        if action == 0:  # Continue on route
            self._continue_on_route(bus_id)
        elif action == 1:  # Go to high demand stop
            self._go_to_high_demand(bus_id)
        elif action == 2:  # Skip low demand stop
            self._skip_low_demand(bus_id)
        elif action == 3:  # Hold at current location
            self._hold_bus(bus_id)
    
    def _continue_on_route(self, bus_id: int):
        """Continue following the assigned route"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        if bus["next_stop_index"] < len(route.stops):
            next_stop_id = route.stops[bus["next_stop_index"]]
            next_stop = self.stops[next_stop_id]
            
            # Move towards next stop
            dx = next_stop.x - bus["x"]
            dy = next_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 2:  # Arrived at stop
                self._process_bus_arrival(bus_id, next_stop_id)
                bus["next_stop_index"] = (bus["next_stop_index"] + 1) % len(route.stops)
                bus["current_stop"] = next_stop_id
            else:
                # Move towards next stop
                bus["x"] += int(dx / max(1, distance) * bus["speed"])
                bus["y"] += int(dy / max(1, distance) * bus["speed"])
    
    def _go_to_high_demand(self, bus_id: int):
        """Route bus to highest demand stop"""
        bus = self.buses[bus_id]
        
        # Find highest demand stop
        max_demand = 0
        target_stop_id = None
        
        for stop_id, stop in self.stops.items():
            demand = self.passengers[stop_id]["queue_length"]
            if demand > max_demand:
                max_demand = demand
                target_stop_id = stop_id
        
        if target_stop_id:
            target_stop = self.stops[target_stop_id]
            
            # Move towards target stop
            dx = target_stop.x - bus["x"]
            dy = target_stop.y - bus["y"]
            distance = (dx**2 + dy**2)**0.5
            
            if distance < 2:  # Arrived at stop
                self._process_bus_arrival(bus_id, target_stop_id)
                bus["current_stop"] = target_stop_id
            else:
                # Move towards target stop
                bus["x"] += int(dx / max(1, distance) * bus["speed"])
                bus["y"] += int(dy / max(1, distance) * bus["speed"])
    
    def _skip_low_demand(self, bus_id: int):
        """Skip low demand stops and go to next high demand stop"""
        bus = self.buses[bus_id]
        route = self.routes[bus["route_id"]]
        
        # Find next high demand stop on route
        for i in range(len(route.stops)):
            next_stop_id = route.stops[(bus["next_stop_index"] + i) % len(route.stops)]
            if self.passengers[next_stop_id]["queue_length"] > 2:  # High demand threshold
                bus["next_stop_index"] = (bus["next_stop_index"] + i) % len(route.stops)
                break
        
        self._continue_on_route(bus_id)
    
    def _hold_bus(self, bus_id: int):
        """Hold bus at current location"""
        bus = self.buses[bus_id]
        bus["status"] = "holding"
        # Bus stays at current position
    
    def _process_bus_arrival(self, bus_id: int, stop_id: str):
        """Process bus arrival at stop"""
        bus = self.buses[bus_id]
        stop_passengers = self.passengers[stop_id]
        
        # Drop off passengers
        passengers_to_drop = [p for p in bus.get("passengers", []) if p["destination"] == stop_id]
        for passenger in passengers_to_drop:
            bus["passengers"].remove(passenger)
            bus["load"] -= 1
        
        # Pick up passengers
        passengers_to_pickup = []
        for passenger in stop_passengers["waiting"][:]:
            if bus["load"] < bus["capacity"]:
                passengers_to_pickup.append(passenger)
                stop_passengers["waiting"].remove(passenger)
                bus["load"] += 1
        
        # Add picked up passengers to bus
        if not bus.get("passengers"):
            bus["passengers"] = []
        bus["passengers"].extend(passengers_to_pickup)
        
        # Update stop queue
        stop_passengers["queue_length"] = len(stop_passengers["waiting"])
    
    def update_wait_times(self):
        """Update passenger wait times"""
        for stop_id, stop_passengers in self.passengers.items():
            for passenger in stop_passengers["waiting"]:
                passenger["wait_time"] += 1
            
            # Update total wait time
            stop_passengers["total_wait_time"] = sum(p["wait_time"] for p in stop_passengers["waiting"])
    
    def calculate_reward(self) -> float:
        """Calculate reward for RL training"""
        # Reward components
        total_wait_time = sum(stop["total_wait_time"] for stop in self.passengers.values())
        total_passengers = sum(len(stop["waiting"]) for stop in self.passengers.values())
        avg_wait_time = total_wait_time / max(1, total_passengers)
        
        # Bus load balance
        bus_loads = [bus["load"] for bus in self.buses.values()]
        load_std = np.std(bus_loads) if bus_loads else 0
        
        # Reward = -avg_wait - 2*overcrowd - 0.1*load_std
        reward = -avg_wait_time - 2 * max(0, load_std - 10) - 0.1 * load_std
        
        return reward
    
    def step(self, actions: List[int]) -> Tuple[np.ndarray, float, bool, Dict]:
        """Perform one simulation step with RL actions"""
        self.simulation_time += 1
        
        # Generate new passengers
        self.generate_passengers()
        
        # Apply RL actions to buses
        for i, bus_id in enumerate(self.buses.keys()):
            if i < len(actions):
                self.apply_action(bus_id, actions[i])
        
        # Update wait times
        self.update_wait_times()
        
        # Get new observation
        obs = self.get_observation()
        
        # Calculate reward
        reward = self.calculate_reward()
        
        # Check if episode is done
        done = self.simulation_time >= 1000  # 1000 time steps
        
        # Get info
        info = {
            "simulation_time": self.simulation_time,
            "total_passengers": sum(len(stop["waiting"]) for stop in self.passengers.values()),
            "avg_wait_time": reward
        }
        
        return obs, reward, done, info
    
    def reset(self) -> Tuple[np.ndarray, Dict]:
        """Reset the environment"""
        self.simulation_time = 0
        
        # Reset buses to starting positions
        for bus_id, bus in self.buses.items():
            route = self.routes[bus["route_id"]]
            bus["x"] = self.stops[route.stops[0]].x
            bus["y"] = self.stops[route.stops[0]].y
            bus["load"] = 0
            bus["next_stop_index"] = 0
            bus["status"] = "moving"
            bus["passengers"] = []
        
        # Reset passenger queues
        for stop_id in self.passengers.keys():
            self.passengers[stop_id] = {
                "waiting": [],
                "total_wait_time": 0.0,
                "queue_length": 0
            }
        
        obs = self.get_observation()
        info = {"simulation_time": 0}
        
        return obs, info

class SimpleRLAgent:
    """Simple RL agent for bus dispatch"""
    
    def __init__(self, observation_space_size: int, action_space_size: int):
        self.observation_space_size = observation_space_size
        self.action_space_size = action_space_size
        
        # Simple Q-learning parameters
        self.learning_rate = 0.1
        self.epsilon = 0.1  # Exploration rate
        self.gamma = 0.9  # Discount factor
        
        # Q-table (simplified)
        self.q_table = {}
        
    def get_action(self, observation: np.ndarray) -> int:
        """Get action from observation"""
        # Convert observation to state key
        state_key = tuple(observation.astype(int))
        
        # Initialize Q-values if not seen before
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_space_size)
        
        # Epsilon-greedy action selection
        if random.random() < self.epsilon:
            return random.randint(0, self.action_space_size - 1)
        else:
            return np.argmax(self.q_table[state_key])
    
    def update(self, observation: np.ndarray, action: int, reward: float, 
               next_observation: np.ndarray, done: bool):
        """Update Q-values"""
        state_key = tuple(observation.astype(int))
        next_state_key = tuple(next_observation.astype(int))
        
        # Initialize Q-values if not seen before
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.action_space_size)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.action_space_size)
        
        # Q-learning update
        current_q = self.q_table[state_key][action]
        if done:
            target_q = reward
        else:
            target_q = reward + self.gamma * np.max(self.q_table[next_state_key])
        
        self.q_table[state_key][action] = current_q + self.learning_rate * (target_q - current_q)
    
    def save_model(self, filepath: str):
        """Save trained model"""
        model_data = {
            "q_table": {str(k): v.tolist() for k, v in self.q_table.items()},
            "observation_space_size": self.observation_space_size,
            "action_space_size": self.action_space_size,
            "learning_rate": self.learning_rate,
            "epsilon": self.epsilon,
            "gamma": self.gamma
        }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f)
        
        print(f"✅ Saved RL model to {filepath}")
    
    def load_model(self, filepath: str):
        """Load trained model"""
        with open(filepath, 'r') as f:
            model_data = json.load(f)
        
        self.q_table = {eval(k): np.array(v) for k, v in model_data["q_table"].items()}
        self.observation_space_size = model_data["observation_space_size"]
        self.action_space_size = model_data["action_space_size"]
        self.learning_rate = model_data["learning_rate"]
        self.epsilon = model_data["epsilon"]
        self.gamma = model_data["gamma"]
        
        print(f"✅ Loaded RL model from {filepath}")

def train_manhattan_rl():
    """Train the Manhattan RL model"""
    print("🤖 TRAINING MANHATTAN RL MODEL")
    print("=" * 50)
    
    # Create environment
    env = ManhattanRLEnvironment()
    
    # Create RL agent
    agent = SimpleRLAgent(env.observation_space_size, env.action_space_size)
    
    # Training parameters
    num_episodes = 100
    max_steps = 500
    
    print(f"🚀 Starting training with {num_episodes} episodes...")
    
    # Training loop
    for episode in range(num_episodes):
        obs, info = env.reset()
        total_reward = 0
        
        for step in range(max_steps):
            # Get actions for all buses
            actions = []
            for bus_id in env.buses.keys():
                action = agent.get_action(obs)
                actions.append(action)
            
            # Step environment
            next_obs, reward, done, info = env.step(actions)
            
            # Update agent
            agent.update(obs, actions[0], reward, next_obs, done)  # Simplified update
            
            obs = next_obs
            total_reward += reward
            
            if done:
                break
        
        # Print progress
        if episode % 10 == 0:
            print(f"Episode {episode}: Total Reward = {total_reward:.2f}")
    
    # Save trained model
    agent.save_model("manhattan_rl_model.json")
    
    print("✅ Manhattan RL model training completed!")
    return agent

def main():
    """Main training function"""
    print("🗽 MANHATTAN RL TRAINING")
    print("=" * 50)
    print("🚌 Training dynamic bus routing")
    print("📍 Real Manhattan stops and routes")
    print("🎯 Demand-responsive dispatch")
    print("=" * 50)
    
    # Train the model
    agent = train_manhattan_rl()
    
    print("\n📊 TRAINING SUMMARY:")
    print(f"  Episodes: 100")
    print(f"  Max Steps: 500")
    print(f"  Model saved: manhattan_rl_model.json")
    print(f"  Q-table size: {len(agent.q_table)}")
    
    return agent

if __name__ == "__main__":
    agent = main()
