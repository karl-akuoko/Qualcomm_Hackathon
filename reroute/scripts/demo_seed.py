#!/usr/bin/env python3
"""
Demo seed script for the bus routing simulation.
Creates a deterministic demo scenario with predefined events.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
import requests
import websockets
import websocket


class DemoController:
    """Controls the demo simulation with predefined scenarios."""
    
    def __init__(self, api_base: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000/ws/live"):
        self.api_base = api_base
        self.ws_url = ws_url
        self.session = requests.Session()
        
    def api_call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make API call to simulation server."""
        try:
            if method == "GET":
                response = self.session.get(f"{self.api_base}{endpoint}")
            elif method == "POST":
                response = self.session.post(f"{self.api_base}{endpoint}", json=data)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API call failed: {e}")
            return {}
    
    def wait_for_condition(self, condition_func, timeout: int = 30, check_interval: float = 1.0) -> bool:
        """Wait for a condition to be met."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(check_interval)
        return False
    
    def run_demo_script(self):
        """Run the complete demo script."""
        print("🚌 Starting Bus Routing Demo")
        print("=" * 50)
        
        # Step 1: Setup
        print("\n📋 Step 1: Setup")
        print("- Initializing simulation...")
        
        # Reset simulation
        self.api_call("/reset", "POST", {"seed": 42})
        time.sleep(1)
        
        # Set to static mode
        self.api_call("/mode", "POST", {"mode": "static"})
        time.sleep(1)
        
        # Start simulation
        self.api_call("/start", "POST")
        print("✓ Simulation started in static mode")
        
        # Step 2: Show baseline performance
        print("\n📊 Step 2: Baseline Performance (30 seconds)")
        print("- Observing static schedule performance...")
        
        baseline_start = time.time()
        baseline_kpis = []
        
        while time.time() - baseline_start < 30:
            status = self.api_call("/kpis")
            if status.get("current"):
                baseline_kpis.append(status["current"])
            time.sleep(2)
        
        avg_baseline_wait = sum(kpi.get("avg_wait", 0) for kpi in baseline_kpis) / len(baseline_kpis)
        print(f"✓ Baseline avg wait time: {avg_baseline_wait:.2f} seconds")
        
        # Step 3: Switch to RL
        print("\n🤖 Step 3: Switch to RL Policy (45 seconds)")
        print("- Switching to RL mode...")
        
        self.api_call("/mode", "POST", {"mode": "rl"})
        time.sleep(2)
        
        print("✓ RL policy activated")
        print("- Observing RL performance improvement...")
        
        rl_start = time.time()
        rl_kpis = []
        
        while time.time() - rl_start < 45:
            status = self.api_call("/kpis")
            if status.get("current"):
                rl_kpis.append(status["current"])
            time.sleep(2)
        
        avg_rl_wait = sum(kpi.get("avg_wait", 0) for kpi in rl_kpis) / len(rl_kpis)
        improvement = ((avg_baseline_wait - avg_rl_wait) / avg_baseline_wait) * 100
        print(f"✓ RL avg wait time: {avg_rl_wait:.2f} seconds")
        print(f"✓ Improvement: {improvement:.1f}%")
        
        # Step 4: Road closure test
        print("\n🚧 Step 4: Road Closure Test (60 seconds)")
        print("- Triggering road closure...")
        
        closure_result = self.api_call("/stress", "POST", {"type": "closure"})
        print(f"✓ Road closure triggered: {closure_result.get('disruption_id', 'Unknown')}")
        
        print("- Observing resilience...")
        resilience_start = time.time()
        resilience_kpis = []
        
        while time.time() - resilience_start < 60:
            status = self.api_call("/kpis")
            if status.get("current"):
                resilience_kpis.append(status["current"])
            time.sleep(2)
        
        avg_resilience_wait = sum(kpi.get("avg_wait", 0) for kpi in resilience_kpis) / len(resilience_kpis)
        print(f"✓ Resilience avg wait: {avg_resilience_wait:.2f} seconds")
        
        # Step 5: Demand surge test
        print("\n👥 Step 5: Demand Surge Test (45 seconds)")
        print("- Triggering demand surge...")
        
        surge_result = self.api_call("/stress", "POST", {"type": "surge"})
        print(f"✓ Demand surge triggered: {surge_result.get('disruption_id', 'Unknown')}")
        
        print("- Observing surge handling...")
        surge_start = time.time()
        surge_kpis = []
        
        while time.time() - surge_start < 45:
            status = self.api_call("/kpis")
            if status.get("current"):
                surge_kpis.append(status["current"])
            time.sleep(2)
        
        avg_surge_wait = sum(kpi.get("avg_wait", 0) for kpi in surge_kpis) / len(surge_kpis)
        print(f"✓ Surge avg wait: {avg_surge_wait:.2f} seconds")
        
        # Step 6: Final results
        print("\n📈 Step 6: Final Results")
        print("- Calculating performance metrics...")
        
        final_status = self.api_call("/kpis")
        final_kpis = final_status.get("current", {})
        
        print("\n" + "=" * 50)
        print("🎯 DEMO RESULTS SUMMARY")
        print("=" * 50)
        
        print(f"📊 Baseline Performance:")
        print(f"   • Average Wait: {avg_baseline_wait:.2f}s")
        print(f"   • 90th Percentile: {final_kpis.get('p90_wait', 0):.2f}s")
        print(f"   • Load Std Dev: {final_kpis.get('load_std', 0):.2f}")
        
        print(f"\n🤖 RL Performance:")
        print(f"   • Average Wait: {avg_rl_wait:.2f}s")
        print(f"   • Improvement: {improvement:.1f}%")
        print(f"   • Resilience: {avg_resilience_wait:.2f}s (during closure)")
        print(f"   • Surge Handling: {avg_surge_wait:.2f}s (during surge)")
        
        print(f"\n✅ Success Criteria Check:")
        print(f"   • Wait Time Improvement: {'✓' if improvement >= 20 else '✗'} (Target: ≥20%)")
        print(f"   • Resilience: {'✓' if avg_resilience_wait <= avg_rl_wait * 1.2 else '✗'} (Target: ≤120% of normal)")
        print(f"   • Surge Handling: {'✓' if avg_surge_wait <= avg_baseline_wait else '✗'} (Target: Better than baseline)")
        
        print(f"\n🏆 Demo Status: {'SUCCESS' if improvement >= 20 else 'PARTIAL SUCCESS'}")
        
        # Stop simulation
        self.api_call("/stop", "POST")
        print("\n✓ Demo completed - simulation stopped")
        
        return {
            "baseline_wait": avg_baseline_wait,
            "rl_wait": avg_rl_wait,
            "improvement": improvement,
            "resilience_wait": avg_resilience_wait,
            "surge_wait": avg_surge_wait,
            "success": improvement >= 20
        }


def main():
    """Main demo execution."""
    print("Bus Routing Simulation Demo Controller")
    print("Make sure the simulation server is running on localhost:8000")
    
    controller = DemoController()
    
    try:
        results = controller.run_demo_script()
        
        # Save results
        with open("demo_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDemo results saved to demo_results.json")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        controller.api_call("/stop", "POST")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        controller.api_call("/stop", "POST")


if __name__ == "__main__":
    main()
