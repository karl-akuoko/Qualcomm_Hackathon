"""
ONNX export functionality for trained RL models.
Converts PyTorch models to ONNX format for on-device inference.
"""

import os
import torch
import torch.nn as nn
import onnx
import onnxruntime as ort
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import json
import time

from stable_baselines3 import PPO
from stable_baselines3.common.policies import BasePolicy


class ONNXExporter:
    """Export Stable Baselines3 models to ONNX format."""
    
    def __init__(self, model_dir: str = "./models"):
        self.model_dir = model_dir
        self.onnx_dir = os.path.join(model_dir, "onnx")
        os.makedirs(self.onnx_dir, exist_ok=True)
    
    def export_ppo_model(self, 
                        model_path: str,
                        output_path: str = None,
                        input_shape: Tuple[int, ...] = None) -> str:
        """
        Export PPO model to ONNX format.
        
        Args:
            model_path: Path to trained PPO model
            output_path: Output path for ONNX model (optional)
            input_shape: Input shape for the model (obs_dim,)
        
        Returns:
            onnx_path: Path to exported ONNX model
        """
        print(f"Loading PPO model from {model_path}")
        
        # Load trained model
        model = PPO.load(model_path)
        
        # Get observation space
        if input_shape is None:
            # Default observation shape for our environment
            input_shape = (300,)  # Based on our environment design
        
        # Create dummy input
        dummy_input = torch.randn(1, *input_shape)
        
        # Extract policy network
        policy_net = model.policy
        
        # Set to evaluation mode
        policy_net.eval()
        
        # Export to ONNX
        if output_path is None:
            model_name = os.path.basename(model_path)
            output_path = os.path.join(self.onnx_dir, f"{model_name}.onnx")
        
        print(f"Exporting to ONNX: {output_path}")
        
        # Export the policy network
        torch.onnx.export(
            policy_net,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=11,
            do_constant_folding=True,
            input_names=['observations'],
            output_names=['actions', 'value'],
            dynamic_axes={
                'observations': {0: 'batch_size'},
                'actions': {0: 'batch_size'},
                'value': {0: 'batch_size'}
            }
        )
        
        # Verify ONNX model
        self._verify_onnx_model(output_path, input_shape)
        
        print(f"Successfully exported ONNX model to: {output_path}")
        return output_path
    
    def _verify_onnx_model(self, onnx_path: str, input_shape: Tuple[int, ...]):
        """Verify exported ONNX model."""
        try:
            # Load ONNX model
            onnx_model = onnx.load(onnx_path)
            onnx.checker.check_model(onnx_model)
            
            # Test inference with ONNX Runtime
            session = ort.InferenceSession(onnx_path)
            
            # Create test input
            test_input = np.random.randn(1, *input_shape).astype(np.float32)
            
            # Run inference
            outputs = session.run(None, {'observations': test_input})
            
            print(f"ONNX model verification successful")
            print(f"  Output shapes: {[output.shape for output in outputs]}")
            
        except Exception as e:
            print(f"ONNX model verification failed: {e}")
            raise
    
    def optimize_for_mobile(self, onnx_path: str) -> str:
        """
        Optimize ONNX model for mobile deployment.
        
        Args:
            onnx_path: Path to ONNX model
        
        Returns:
            optimized_path: Path to optimized model
        """
        print("Optimizing ONNX model for mobile...")
        
        # Load model
        model = onnx.load(onnx_path)
        
        # Basic optimizations
        from onnx import optimizer
        passes = ['eliminate_identity', 'eliminate_nop_pad', 'fuse_consecutive_transposes']
        
        try:
            optimized_model = optimizer.optimize(model, passes)
        except:
            # If optimization fails, use original model
            print("Warning: ONNX optimization failed, using original model")
            optimized_model = model
        
        # Save optimized model
        base_name = os.path.splitext(os.path.basename(onnx_path))[0]
        optimized_path = os.path.join(self.onnx_dir, f"{base_name}_optimized.onnx")
        onnx.save(optimized_model, optimized_path)
        
        print(f"Optimized model saved to: {optimized_path}")
        return optimized_path
    
    def create_metadata(self, 
                       model_path: str,
                       onnx_path: str,
                       config: Dict) -> str:
        """
        Create metadata file for the ONNX model.
        
        Args:
            model_path: Path to original model
            onnx_path: Path to ONNX model
            config: Model configuration
        
        Returns:
            metadata_path: Path to metadata file
        """
        metadata = {
            'model_info': {
                'original_path': model_path,
                'onnx_path': onnx_path,
                'export_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'framework': 'stable_baselines3',
                'algorithm': 'PPO'
            },
            'model_config': config,
            'inference_info': {
                'input_shape': [1, 300],  # batch_size, obs_dim
                'output_shapes': [
                    [1, 6, 4],  # actions: batch_size, num_buses, action_dim
                    [1, 1]      # value: batch_size, 1
                ],
                'dtype': 'float32'
            },
            'performance_target': {
                'device': 'Snapdragon X Elite',
                'expected_latency_ms': '< 10',
                'memory_usage_mb': '< 100'
            }
        }
        
        metadata_path = os.path.join(self.onnx_dir, "model_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Metadata saved to: {metadata_path}")
        return metadata_path


class ONNXInference:
    """ONNX Runtime inference wrapper for deployed models."""
    
    def __init__(self, onnx_path: str):
        self.onnx_path = onnx_path
        self.session = None
        self.input_name = None
        self.output_names = None
        
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize ONNX Runtime session."""
        try:
            # Create session with optimizations for mobile
            providers = ['CPUExecutionProvider']
            
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.intra_op_num_threads = 4
            session_options.inter_op_num_threads = 1
            
            self.session = ort.InferenceSession(
                self.onnx_path,
                sess_options=session_options,
                providers=providers
            )
            
            # Get input/output names
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            print(f"ONNX Runtime session initialized successfully")
            print(f"  Input: {self.input_name}")
            print(f"  Outputs: {self.output_names}")
            
        except Exception as e:
            print(f"Failed to initialize ONNX Runtime session: {e}")
            raise
    
    def predict(self, observations: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Run inference on observations.
        
        Args:
            observations: Input observations (batch_size, obs_dim)
        
        Returns:
            actions: Predicted actions (batch_size, num_buses, action_dim)
            value: Value estimate (batch_size, 1)
        """
        if self.session is None:
            raise RuntimeError("Session not initialized")
        
        # Ensure correct dtype
        observations = observations.astype(np.float32)
        
        # Run inference
        start_time = time.time()
        outputs = self.session.run(self.output_names, {self.input_name: observations})
        inference_time = time.time() - start_time
        
        actions = outputs[0]
        value = outputs[1]
        
        return actions, value
    
    def benchmark(self, num_runs: int = 100) -> Dict[str, float]:
        """
        Benchmark inference performance.
        
        Args:
            num_runs: Number of benchmark runs
        
        Returns:
            performance_metrics: Dictionary with timing statistics
        """
        # Create dummy input
        dummy_input = np.random.randn(1, 300).astype(np.float32)
        
        # Warmup
        for _ in range(10):
            self.predict(dummy_input)
        
        # Benchmark
        times = []
        for _ in range(num_runs):
            start_time = time.time()
            self.predict(dummy_input)
            end_time = time.time()
            times.append((end_time - start_time) * 1000)  # Convert to ms
        
        # Calculate statistics
        performance_metrics = {
            'mean_latency_ms': np.mean(times),
            'std_latency_ms': np.std(times),
            'min_latency_ms': np.min(times),
            'max_latency_ms': np.max(times),
            'p95_latency_ms': np.percentile(times, 95),
            'throughput_fps': 1000.0 / np.mean(times)
        }
        
        print(f"Benchmark Results ({num_runs} runs):")
        print(f"  Mean latency: {performance_metrics['mean_latency_ms']:.2f} ms")
        print(f"  Std latency: {performance_metrics['std_latency_ms']:.2f} ms")
        print(f"  P95 latency: {performance_metrics['p95_latency_ms']:.2f} ms")
        print(f"  Throughput: {performance_metrics['throughput_fps']:.1f} FPS")
        
        return performance_metrics


def export_model_pipeline(model_path: str, config: Dict = None) -> Dict[str, str]:
    """
    Complete pipeline for exporting a trained model to ONNX.
    
    Args:
        model_path: Path to trained model
        config: Model configuration
    
    Returns:
        export_info: Dictionary with paths to exported files
    """
    exporter = ONNXExporter()
    
    # Export to ONNX
    onnx_path = exporter.export_ppo_model(model_path)
    
    # Optimize for mobile
    optimized_path = exporter.optimize_for_mobile(onnx_path)
    
    # Create metadata
    if config is None:
        config = {}
    metadata_path = exporter.create_metadata(model_path, optimized_path, config)
    
    export_info = {
        'original_model': model_path,
        'onnx_model': onnx_path,
        'optimized_model': optimized_path,
        'metadata': metadata_path
    }
    
    return export_info


def test_onnx_inference(onnx_path: str, num_tests: int = 10):
    """Test ONNX inference with random inputs."""
    print(f"Testing ONNX inference with {num_tests} random inputs...")
    
    # Initialize inference
    onnx_inference = ONNXInference(onnx_path)
    
    # Run tests
    for i in range(num_tests):
        # Create random observation
        obs = np.random.randn(1, 300).astype(np.float32)
        
        # Run inference
        actions, value = onnx_inference.predict(obs)
        
        print(f"Test {i+1}: Actions shape: {actions.shape}, Value shape: {value.shape}")
    
    # Benchmark
    benchmark_results = onnx_inference.benchmark()
    
    return benchmark_results


if __name__ == "__main__":
    # Example usage
    model_path = "./models/final_model.zip"
    
    if os.path.exists(model_path):
        # Export model
        export_info = export_model_pipeline(model_path)
        print("Export completed:")
        for key, path in export_info.items():
            print(f"  {key}: {path}")
        
        # Test inference
        test_onnx_inference(export_info['optimized_model'])
    else:
        print(f"Model not found at {model_path}")
        print("Please train a model first using train.py")
