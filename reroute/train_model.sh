#!/bin/bash
echo "Training RL model..."
cd rl
python train.py --mode train --timesteps 100000
