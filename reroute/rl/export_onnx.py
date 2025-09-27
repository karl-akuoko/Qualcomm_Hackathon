import torch
import torch.onnx
import numpy as np
from stable_baselines3 import PPO
import onnx
import onnxruntime as ort
import sys
sys.path.append('../env')
from wrappers import BusDispatchEnv

def export_ppo_to_onnx(model_path: str, onnx_path: str, opset_version: int = 11):
    """Export trained PPO model to ONNX format for device inference"""
    
    print(f"Loading PPO model from {model_path}")
    
    # Load the trained model
    model = PPO.load(model_path)
    
    # Create dummy environment to get observation space
    env = BusDispatchEnv(
        grid_size=(20, 20),
        num_stops=32,
        num_buses=6,
        seed=42
    )
    
    # Get observation dimensions
    obs_space_shape = env.observation_space.shape
    print(f"Observation space shape: {obs_space_shape}")
    
    # Extract the policy network
    policy_net = model.policy.mlp_extractor
    action_net = model.policy.action_net
    
    # Create a wrapper that combines feature extraction and action prediction
    class ONNXPolicyWrapper(torch.nn.Module):
        def __init__(self, mlp_extractor, action_net):
            super().__init__()
            self.mlp_extractor = mlp_extractor
            self.action_net = action_net
            
        def forward(self, observations):
            # Extract features
            features = self.mlp_extractor.forward_actor(observations)
            # Get action logits
            action_logits = self.action_net(features)
            # Return action probabilities (softmax) and raw logits
            action_probs = torch.softmax(action_logits, dim=-1)
            return action_probs, action_logits
    
    # Create the wrapper
    onnx_model = ONNXPolicyWrapper(policy_net, action_net)
    onnx_model.eval()
    
    # Create dummy input
    dummy_input = torch.randn(1, *obs_space_shape, dtype=torch.float32)
    
    print("Exporting to ONNX...")
    
    # Export to ONNX
    torch.onnx.export(
        onnx_model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=['observations'],
        output_names=['action_probs', 'action_logits'],
        dynamic_axes={
            'observations': {0: 'batch_size'},
            'action_probs': {0: 'batch_size'},
            'action_logits': {0: 'batch_size'}
        }
    )
    
    print(f"Model exported to {onnx_path}")
    
    # Verify the ONNX model
    verify_onnx_model(onnx_path, dummy_input, onnx_model)
    
    return onnx_path

def verify_onnx_model(onnx_path: str, test_input: torch.Tensor, original_model):
    """Verify ONNX model produces same outputs as original"""
    
    print("Verifying ONNX model...")
    
    # Load ONNX model
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    print("ONNX model is valid")
    
    # Create ONNX Runtime session
    ort_session = ort.InferenceSession(onnx_path)
    
    # Test inference
    test_input_np = test_input.detach().numpy()
    
    # Original model output
    original_model.eval()
    with torch.no_grad():
        orig_probs, orig_logits = original_model(test_input)
        orig_probs_np = orig_probs.numpy()
        orig_logits_np = orig_logits.numpy()
    
    # ONNX model output
    ort_inputs = {ort_session.get_inputs()[0].name: test_input_np}
    onnx_probs, onnx_logits = ort_session.run(None, ort_inputs)
    
    # Compare outputs
    prob_diff = np.abs(orig_probs_np - onnx_probs).max()
    logit_diff = np.abs(orig_logits_np - onnx_logits).max()
    
    print(f"Max probability difference: {prob_diff}")
    print(f"Max logit difference: {logit_diff}")
    
    if prob_diff < 1e-5 and logit_diff < 1e-5:
        print("✓ ONNX model verification passed!")
    else:
        print("✗ ONNX model verification failed!")
        print("Large differences detected between original and ONNX outputs")
    
    return prob_diff < 1e-5 and logit_diff < 1e-5

class ONNXPolicyInference:
    """ONNX-based policy inference for deployment"""
    
    def __init__(self, onnx_path: str):
        self.session = ort.InferenceSession(onnx_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        print(f"Loaded ONNX model: {onnx_path}")
        print(f"Input name: {self.input_name}")
        print(f"Output names: {self.output_names}")
    
    def predict(self, observation: np.ndarray, deterministic: bool = True):
        """Predict action given observation"""
        
        # Ensure correct shape (add batch dimension if needed)
        if observation.ndim == 1:
            observation = observation.reshape(1, -1)
        
        # Run inference
        ort_inputs = {self.input_name: observation.astype(np.float32)}
        action_probs, action_logits = self.session.run(self.output_names, ort_inputs)
        
        if deterministic:
            # Take argmax for each bus
            actions = np.argmax(action_probs, axis=-1)
        else:
            # Sample from distribution
            actions = []
            for i in range(action_probs.shape[0]):
                # action_probs has shape [batch_size, num_buses * num_actions]
                # Reshape to [batch_size, num_buses, num_actions]
                # Assuming 6 buses and 4 actions each
                probs_reshaped = action_probs[i].reshape(6, 4)
                bus_actions = []
                for bus_probs in probs_reshaped:
                    action = np.random.choice(4, p=bus_probs)
                    bus_actions.append(action)
                actions.append(bus_actions)
            actions = np.array(actions)
        
        return actions.squeeze() if actions.shape[0] == 1 else actions
    
    def get_model_info(self):
        """Get model information"""
        inputs_info = []
        for inp in self.session.get_inputs():
            inputs_info.append({
                'name': inp.name,
                'type': inp.type,
                'shape': inp.shape
            })
        
        outputs_info = []
        for out in self.session.get_outputs():
            outputs_info.append({
                'name': out.name,
                'type': out.type,
                'shape': out.shape
            })
        
        return {
            'inputs': inputs_info,
            'outputs': outputs_info
        }

def benchmark_inference(onnx_path: str, num_iterations: int = 1000):
    """Benchmark ONNX inference performance"""
    
    import time
    
    print(f"Benchmarking ONNX inference with {num_iterations} iterations...")
    
    # Create inference engine
    policy = ONNXPolicyInference(onnx_path)
    
    # Create dummy observation
    env = BusDispatchEnv(seed=42)
    obs = env.reset()
    
    # Warm up
    for _ in range(10):
        policy.predict(obs)
    
    # Benchmark
    start_time = time.time()
    for _ in range(num_iterations):
        actions = policy.predict(obs)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = total_time / num_iterations
    
    print(f"Total time: {total_time:.3f} seconds")
    print(f"Average inference time: {avg_time*1000:.3f} ms")
    print(f"Inference rate: {1/avg_time:.1f} Hz")
    
    return avg_time

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export PPO model to ONNX")
    parser.add_argument("--input", type=str, default="ppo_bus_final",
                       help="Input PPO model path")
    parser.add_argument("--output", type=str, default="ppo_bus_policy.onnx",
                       help="Output ONNX model path")
    parser.add_argument("--benchmark", action="store_true",
                       help="Run inference benchmark")
    parser.add_argument("--iterations", type=int, default=1000,
                       help="Benchmark iterations")
    
    args = parser.parse_args()
    
    # Export model
    onnx_path = export_ppo_to_onnx(args.input, args.output)
    
    # Run benchmark if requested
    if args.benchmark:
        benchmark_inference(onnx_path, args.iterations)
    
    print("Export completed successfully!")
