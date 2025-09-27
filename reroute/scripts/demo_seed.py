#!/usr/bin/env python3
"""
Deterministic demo seed script for Bus Dispatch RL system.
Creates reproducible scenarios for demonstrations and testing.
"""

import numpy as np
import json
import sys
import os
sys.path.append('../env')
from wrappers import BusDispatchEnv
from bus import BusMode

class DemoScenario:
    """Predefined demo scenarios with deterministic outcomes"""
    
    def __init__(self, name: str, description: str, duration: float = 300.0):
        self.name = name
        self.description = description
        self.duration = duration
        self.events = []
        self.expected_outcomes = {}
    
    def add_event(self, time: float, event_type: str, params: dict):
        """Add a timed event to the scenario"""
        self.events.append({
            'time': time,
            'type': event_type,
            'params': params
        })
    
    def set_expected_outcome(self, metric: str, min_value: float, max_value: float):
        """Set expected outcome range for a metric"""
        self.expected_outcomes[metric] = {
            'min': min_value,
            'max': max_value
        }

class DemoSeedGenerator:
    """Generates deterministic demo scenarios"""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
        self.scenarios = {}
        self._create_scenarios()
    
    def _create_scenarios(self):
        """Create predefined demo scenarios"""
        
        # Scenario 1: Morning Rush Hour
        morning_rush = DemoScenario(
            "morning_rush",
            "Morning rush hour with high demand and traffic",
            duration=300.0
        )
        morning_rush.add_event(0, "set_time_of_day", {"hour": 8, "minute": 0})
        morning_rush.add_event(30, "traffic_jam", {"center_x": 10, "center_y": 10, "radius": 3, "severity": 2.0})
        morning_rush.add_event(60, "demand_surge", {"stop_id": 210, "multiplier": 2.5})
        morning_rush.add_event(120, "road_closure", {"stop_id": 156})
        morning_rush.set_expected_outcome("avg_wait_improvement", 0.15, 0.35)
        self.scenarios["morning_rush"] = morning_rush
        
        # Scenario 2: Event Surge
        event_surge = DemoScenario(
            "event_surge",
            "Stadium event with massive demand surge",
            duration=240.0
        )
        event_surge.add_event(0, "set_time_of_day", {"hour": 18, "minute": 0})
        event_surge.add_event(30, "demand_surge", {"stop_id": 156, "multiplier": 4.0})
        event_surge.add_event(60, "demand_surge", {"stop_id": 210, "multiplier": 3.5})
        event_surge.add_event(90, "traffic_jam", {"center_x": 8, "center_y": 12, "radius": 4, "severity": 2.5})
        event_surge.set_expected_outcome("overcrowd_improvement", 0.25, 0.45)
        self.scenarios["event_surge"] = event_surge
        
        # Scenario 3: Infrastructure Failure
        infrastructure_failure = DemoScenario(
            "infrastructure_failure",
            "Multiple road closures and traffic disruptions",
            duration=360.0
        )
        infrastructure_failure.add_event(0, "set_time_of_day", {"hour": 14, "minute": 0})
        infrastructure_failure.add_event(60, "road_closure", {"stop_id": 210})
        infrastructure_failure.add_event(90, "road_closure", {"stop_id": 156})
        infrastructure_failure.add_event(120, "traffic_jam", {"center_x": 12, "center_y": 8, "radius": 5, "severity": 3.0})
        infrastructure_failure.add_event(180, "demand_surge", {"stop_id": 78, "multiplier": 2.0})
        infrastructure_failure.set_expected_outcome("resilience_score", 0.6, 0.9)
        self.scenarios["infrastructure_failure"] = infrastructure_failure
        
        # Scenario 4: Gradual Degradation
        gradual_degradation = DemoScenario(
            "gradual_degradation",
            "Gradually increasing traffic and demand",
            duration=420.0
        )
        gradual_degradation.add_event(0, "set_time_of_day", {"hour": 16, "minute": 0})
        gradual_degradation.add_event(30, "traffic_jam", {"center_x": 10, "center_y": 10, "radius": 2, "severity": 1.5})
        gradual_degradation.add_event(90, "traffic_jam", {"center_x": 8, "center_y": 12, "radius": 3, "severity": 2.0})
        gradual_degradation.add_event(150, "demand_surge", {"stop_id": 210, "multiplier": 2.0})
        gradual_degradation.add_event(210, "demand_surge", {"stop_id": 156, "multiplier": 2.5})
        gradual_degradation.add_event(270, "road_closure", {"stop_id": 78})
        gradual_degradation.set_expected_outcome("avg_wait_improvement", 0.20, 0.40)
        self.scenarios["gradual_degradation"] = gradual_degradation
    
    def get_scenario(self, name: str) -> DemoScenario:
        """Get a specific scenario by name"""
        if name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {name}. Available: {list(self.scenarios.keys())}")
        return self.scenarios[name]
    
    def list_scenarios(self) -> list:
        """List all available scenarios"""
        return list(self.scenarios.keys())
    
    def create_custom_scenario(self, name: str, description: str, duration: float = 300.0) -> DemoScenario:
        """Create a custom scenario"""
        scenario = DemoScenario(name, description, duration)
        self.scenarios[name] = scenario
        return scenario

class DemoRunner:
    """Runs demo scenarios with deterministic outcomes"""
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.generator = DemoSeedGenerator(seed)
        self.results = {}
    
    def run_scenario(self, scenario_name: str, mode: str = "rl", render: bool = False) -> dict:
        """Run a specific scenario"""
        
        scenario = self.generator.get_scenario(scenario_name)
        print(f"Running scenario: {scenario.name}")
        print(f"Description: {scenario.description}")
        print(f"Duration: {scenario.duration} seconds")
        
        # Create environment
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,
            max_episode_time=scenario.duration,
            seed=self.seed
        )
        
        # Set mode
        if mode == "rl":
            env.bus_fleet.set_mode(BusMode.RL)
        else:
            env.bus_fleet.set_mode(BusMode.STATIC)
        
        # Reset environment
        obs = env.reset()
        
        # Track metrics
        metrics_history = []
        event_log = []
        
        # Run simulation
        current_time = 0.0
        step = 0
        
        while current_time < scenario.duration:
            # Check for events
            for event in scenario.events:
                if abs(current_time - event['time']) < 0.5:  # Within 0.5 seconds
                    self._apply_event(env, event)
                    event_log.append({
                        'time': current_time,
                        'event': event,
                        'applied': True
                    })
            
            # Generate action
            if mode == "rl":
                # For RL mode, use random actions (in practice, load trained model)
                action = np.random.randint(0, 4, size=env.num_buses)
            else:
                # Static mode - no actions needed
                action = np.zeros(env.num_buses, dtype=int)
            
            # Step environment
            obs, reward, done, info = env.step(action)
            current_time += env.time_step
            step += 1
            
            # Record metrics
            if step % 10 == 0:  # Every 5 seconds
                metrics_history.append({
                    'time': current_time,
                    'reward': reward,
                    'info': info.copy()
                })
            
            if render:
                env.render()
            
            if done:
                break
        
        # Calculate final metrics
        final_metrics = self._calculate_final_metrics(metrics_history, scenario)
        
        # Store results
        self.results[scenario_name] = {
            'scenario': scenario.name,
            'mode': mode,
            'duration': current_time,
            'steps': step,
            'metrics_history': metrics_history,
            'event_log': event_log,
            'final_metrics': final_metrics,
            'expected_outcomes': scenario.expected_outcomes
        }
        
        return self.results[scenario_name]
    
    def _apply_event(self, env, event: dict):
        """Apply an event to the environment"""
        event_type = event['type']
        params = event['params']
        
        if event_type == "set_time_of_day":
            # Set simulation time (simplified)
            hour = params.get('hour', 12)
            minute = params.get('minute', 0)
            print(f"Setting time to {hour:02d}:{minute:02d}")
            
        elif event_type == "traffic_jam":
            center_x = params.get('center_x', 10)
            center_y = params.get('center_y', 10)
            radius = params.get('radius', 3)
            severity = params.get('severity', 2.0)
            env.apply_disruption('traffic', {
                'center_x': center_x,
                'center_y': center_y,
                'radius': radius,
                'severity': severity
            })
            print(f"Applied traffic jam at ({center_x}, {center_y}) with severity {severity}")
            
        elif event_type == "demand_surge":
            stop_id = params.get('stop_id', 210)
            multiplier = params.get('multiplier', 2.0)
            env.apply_disruption('surge', {
                'stop_id': stop_id,
                'multiplier': multiplier
            })
            print(f"Applied demand surge at stop {stop_id} with multiplier {multiplier}")
            
        elif event_type == "road_closure":
            stop_id = params.get('stop_id', 210)
            env.apply_disruption('closure', {'stop_id': stop_id})
            print(f"Applied road closure at stop {stop_id}")
    
    def _calculate_final_metrics(self, metrics_history: list, scenario: DemoScenario) -> dict:
        """Calculate final performance metrics"""
        if not metrics_history:
            return {}
        
        # Extract metrics from history
        rewards = [m['reward'] for m in metrics_history]
        wait_times = []
        load_stds = []
        
        for m in metrics_history:
            if 'info' in m and 'rl_stats' in m['info']:
                wait_times.append(m['info']['rl_stats']['avg_wait'])
                load_stds.append(m['info']['rl_stats']['load_std'])
        
        # Calculate improvements
        improvements = {}
        if len(metrics_history) > 10:
            early_metrics = metrics_history[:10]
            late_metrics = metrics_history[-10:]
            
            early_wait = np.mean([m['info']['rl_stats']['avg_wait'] for m in early_metrics if 'rl_stats' in m['info']])
            late_wait = np.mean([m['info']['rl_stats']['avg_wait'] for m in late_metrics if 'rl_stats' in m['info']])
            
            if early_wait > 0:
                improvements['wait_time_trend'] = (early_wait - late_wait) / early_wait
        
        return {
            'total_reward': np.sum(rewards),
            'avg_reward': np.mean(rewards),
            'final_wait_time': wait_times[-1] if wait_times else 0,
            'avg_wait_time': np.mean(wait_times) if wait_times else 0,
            'final_load_std': load_stds[-1] if load_stds else 0,
            'avg_load_std': np.mean(load_stds) if load_stds else 0,
            'improvements': improvements
        }
    
    def compare_scenarios(self, scenario_name: str) -> dict:
        """Compare RL vs Static performance for a scenario"""
        
        print(f"Comparing RL vs Static for scenario: {scenario_name}")
        
        # Run with RL mode
        rl_results = self.run_scenario(scenario_name, mode="rl")
        
        # Run with Static mode
        static_results = self.run_scenario(scenario_name, mode="static")
        
        # Calculate comparison
        comparison = {
            'scenario': scenario_name,
            'rl_results': rl_results,
            'static_results': static_results,
            'improvements': {}
        }
        
        # Calculate improvements
        rl_metrics = rl_results['final_metrics']
        static_metrics = static_results['final_metrics']
        
        for metric in ['avg_wait_time', 'avg_load_std']:
            if metric in rl_metrics and metric in static_metrics:
                rl_val = rl_metrics[metric]
                static_val = static_metrics[metric]
                if static_val > 0:
                    improvement = (static_val - rl_val) / static_val
                    comparison['improvements'][metric] = improvement
        
        return comparison
    
    def generate_report(self, output_path: str = None) -> str:
        """Generate comprehensive demo report"""
        
        report = []
        report.append("=" * 60)
        report.append("BUS DISPATCH RL DEMO REPORT")
        report.append("=" * 60)
        report.append("")
        
        for scenario_name, results in self.results.items():
            report.append(f"SCENARIO: {scenario_name.upper()}")
            report.append(f"Mode: {results['mode']}")
            report.append(f"Duration: {results['duration']:.1f} seconds")
            report.append(f"Steps: {results['steps']}")
            
            metrics = results['final_metrics']
            if metrics:
                report.append(f"Total Reward: {metrics.get('total_reward', 0):.2f}")
                report.append(f"Avg Wait Time: {metrics.get('avg_wait_time', 0):.2f} minutes")
                report.append(f"Avg Load Std: {metrics.get('avg_load_std', 0):.2f}")
            
            report.append("")
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
            print(f"Report saved to {output_path}")
        
        return report_text

def main():
    """Main demo script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Bus Dispatch RL Demo Scenarios")
    parser.add_argument("--scenario", type=str, default="morning_rush",
                       choices=["morning_rush", "event_surge", "infrastructure_failure", "gradual_degradation"],
                       help="Scenario to run")
    parser.add_argument("--mode", type=str, default="rl", choices=["rl", "static"],
                       help="Mode to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--render", action="store_true", help="Render simulation")
    parser.add_argument("--compare", action="store_true", help="Compare RL vs Static")
    parser.add_argument("--output", type=str, help="Output file for results")
    
    args = parser.parse_args()
    
    # Create demo runner
    runner = DemoRunner(seed=args.seed)
    
    if args.compare:
        # Run comparison
        comparison = runner.compare_scenarios(args.scenario)
        print("Comparison Results:")
        print(f"RL Avg Wait: {comparison['rl_results']['final_metrics']['avg_wait_time']:.2f}")
        print(f"Static Avg Wait: {comparison['static_results']['final_metrics']['avg_wait_time']:.2f}")
        print(f"Improvement: {comparison['improvements'].get('avg_wait_time', 0)*100:.1f}%")
    else:
        # Run single scenario
        results = runner.run_scenario(args.scenario, mode=args.mode, render=args.render)
        print("Scenario Results:")
        print(f"Total Reward: {results['final_metrics']['total_reward']:.2f}")
        print(f"Avg Wait Time: {results['final_metrics']['avg_wait_time']:.2f} minutes")
    
    # Generate report
    if args.output:
        report = runner.generate_report(args.output)
        print(f"Report saved to {args.output}")

if __name__ == "__main__":
    main()
