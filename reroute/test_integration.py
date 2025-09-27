#!/usr/bin/env python3
"""
Integration test script for Bus Dispatch RL MVP
Tests all major components and their interactions
"""

import sys
import os
import time
import json
import numpy as np
from pathlib import Path

# Add paths for imports
sys.path.append('.')
sys.path.append('env')
sys.path.append('rl')
sys.path.append('server')

def test_environment():
    """Test environment creation and basic functionality"""
    print("Testing environment...")
    
    try:
        from env.wrappers import BusDispatchEnv
        
        # Create environment
        env = BusDispatchEnv(
            grid_size=(20, 20),
            num_stops=32,
            num_buses=6,
            time_step=0.5,
            max_episode_time=60.0,
            seed=42
        )
        
        # Test reset
        obs = env.reset()
        assert obs.shape == (env.num_buses * 5 + env.num_stops * 1,), f"Wrong obs shape: {obs.shape}"
        print("✓ Environment reset successful")
        
        # Test step
        action = np.random.randint(0, 4, size=env.num_buses)
        obs, reward, done, info = env.step(action)
        assert isinstance(reward, (int, float)), "Reward should be numeric"
        assert isinstance(done, bool), "Done should be boolean"
        assert isinstance(info, dict), "Info should be dictionary"
        print("✓ Environment step successful")
        
        # Test system state
        state = env.get_system_state()
        assert 'buses' in state, "System state should contain buses"
        assert 'stops' in state, "System state should contain stops"
        assert 'kpi' in state, "System state should contain KPI"
        print("✓ System state generation successful")
        
        # Test disruption
        env.apply_disruption('closure', {'stop_id': 210})
        print("✓ Disruption application successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment test failed: {e}")
        return False

def test_rl_training():
    """Test RL training components"""
    print("Testing RL training...")
    
    try:
        from rl.train import create_training_env
        from rl.policies import BusDispatchPolicy
        from stable_baselines3 import PPO
        
        # Test environment creation
        env_func = create_training_env(seed=42)
        env = env_func()
        assert env is not None, "Training environment creation failed"
        print("✓ Training environment creation successful")
        
        # Test policy creation (without actual training)
        policy_kwargs = {
            'features_extractor_class': 'BusDispatchFeaturesExtractor',
            'features_extractor_kwargs': {'features_dim': 128}
        }
        
        # This would normally be used in training
        print("✓ RL training components available")
        
        return True
        
    except Exception as e:
        print(f"✗ RL training test failed: {e}")
        return False

def test_server_components():
    """Test server components"""
    print("Testing server components...")
    
    try:
        from server.state_store import StateStore, SimulationSnapshot
        from server.adapters import StaticDispatcher, DispatcherFactory
        
        # Test state store
        store = StateStore()
        test_state = {
            'time': 100.0,
            'buses': [{'id': 0, 'x': 10, 'y': 10, 'load': 5}],
            'stops': [{'id': 210, 'x': 10, 'y': 10, 'queue_len': 3}],
            'kpi': {'avg_wait': 5.0, 'load_std': 2.0},
            'baseline_kpi': {'avg_wait': 6.0, 'load_std': 3.0}
        }
        
        store.update_state(test_state)
        current_state = store.get_current_state()
        assert current_state is not None, "State store should have current state"
        print("✓ State store functionality successful")
        
        # Test dispatcher factory
        from env.wrappers import BusDispatchEnv
        env = BusDispatchEnv(seed=42)
        dispatcher = DispatcherFactory.create_dispatcher("static", env.bus_fleet)
        assert dispatcher is not None, "Dispatcher creation failed"
        print("✓ Dispatcher creation successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Server components test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoint functionality"""
    print("Testing API endpoints...")
    
    try:
        # Test that we can import the FastAPI app
        from server.fastapi_server import app
        assert app is not None, "FastAPI app should be importable"
        print("✓ FastAPI app import successful")
        
        # Test that we can get routes
        routes = [route.path for route in app.routes]
        expected_routes = ['/mode', '/stress', '/reset', '/status', '/state', '/metrics', '/live']
        
        for route in expected_routes:
            assert any(route in r for r in routes), f"Route {route} not found"
        
        print("✓ API routes configuration successful")
        
        return True
        
    except Exception as e:
        print(f"✗ API endpoints test failed: {e}")
        return False

def test_demo_scenarios():
    """Test demo scenario functionality"""
    print("Testing demo scenarios...")
    
    try:
        from scripts.demo_seed import DemoSeedGenerator, DemoRunner
        
        # Test scenario generator
        generator = DemoSeedGenerator(seed=42)
        scenarios = generator.list_scenarios()
        assert len(scenarios) > 0, "Should have demo scenarios"
        print("✓ Demo scenario generator successful")
        
        # Test scenario creation
        scenario = generator.get_scenario("morning_rush")
        assert scenario.name == "morning_rush", "Should get correct scenario"
        print("✓ Demo scenario retrieval successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Demo scenarios test failed: {e}")
        return False

def test_onnx_export():
    """Test ONNX export functionality"""
    print("Testing ONNX export...")
    
    try:
        from rl.export_onnx import ONNXPolicyInference
        
        # Test that ONNX inference class can be imported
        # (We won't actually test inference without a trained model)
        print("✓ ONNX export components available")
        
        return True
        
    except Exception as e:
        print(f"✗ ONNX export test failed: {e}")
        return False

def test_client_components():
    """Test client component availability"""
    print("Testing client components...")
    
    try:
        # Check that client files exist
        dashboard_file = Path("clients/dashboard/react_dashboard (1).tsx")
        mobile_file = Path("clients/mobile/mobile_app (2).tsx")
        
        assert dashboard_file.exists(), "Dashboard file should exist"
        assert mobile_file.exists(), "Mobile app file should exist"
        
        # Check that they contain expected content
        dashboard_content = dashboard_file.read_text()
        assert "Dashboard" in dashboard_content, "Dashboard should contain Dashboard component"
        
        mobile_content = mobile_file.read_text()
        assert "RiderApp" in mobile_content, "Mobile app should contain RiderApp component"
        
        print("✓ Client components available")
        
        return True
        
    except Exception as e:
        print(f"✗ Client components test failed: {e}")
        return False

def run_integration_test():
    """Run a simple integration test"""
    print("Running integration test...")
    
    try:
        from env.wrappers import BusDispatchEnv
        
        # Create environment
        env = BusDispatchEnv(seed=42)
        obs = env.reset()
        
        # Run a few steps
        for step in range(10):
            action = np.random.randint(0, 4, size=env.num_buses)
            obs, reward, done, info = env.step(action)
            
            if step % 3 == 0:
                # Test system state
                state = env.get_system_state()
                assert 'time' in state, "State should have time"
                assert 'buses' in state, "State should have buses"
                assert 'stops' in state, "State should have stops"
        
        print("✓ Integration test successful")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("BUS DISPATCH RL MVP INTEGRATION TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Environment", test_environment),
        ("RL Training", test_rl_training),
        ("Server Components", test_server_components),
        ("API Endpoints", test_api_endpoints),
        ("Demo Scenarios", test_demo_scenarios),
        ("ONNX Export", test_onnx_export),
        ("Client Components", test_client_components),
        ("Integration", run_integration_test),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name} Test:")
        if test_func():
            passed += 1
        else:
            print(f"✗ {test_name} test failed")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("✓ All tests passed! System is ready for demo.")
        print("\nNext steps:")
        print("1. Run: python setup.py --quick")
        print("2. Start server: ./start_server.sh")
        print("3. Open dashboard: http://localhost:8000")
        return 0
    else:
        print(f"✗ {total - passed} tests failed. Please check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
