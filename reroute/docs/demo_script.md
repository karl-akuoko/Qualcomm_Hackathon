# Bus Routing Demo Script

## Overview
This document outlines the 5-7 minute demo script for the RL-driven bus routing simulation. The demo showcases the system's ability to improve rider wait times and handle disruptions compared to a fixed schedule baseline.

## Demo Setup
- **Duration**: 5-7 minutes
- **Hardware**: Snapdragon X Elite laptop
- **Components**: 
  - Web dashboard (dual maps)
  - Mobile rider app
  - Live simulation server
  - ONNX-powered RL inference

## Demo Flow

### Step 1: Setup (30 seconds)
**Objective**: Initialize the simulation and establish baseline

**Actions**:
1. Open web dashboard at `http://localhost:3000`
2. Show simulation starting in Static mode
3. Display initial grid with buses and stops
4. Point out morning peak demand (7 AM simulation time)

**Key Points**:
- "We're starting with a traditional fixed schedule"
- "Notice the 6 buses following predetermined routes"
- "This represents typical morning rush hour demand"

### Step 2: Baseline Performance (60 seconds)
**Objective**: Show deteriorating performance under fixed schedule

**Actions**:
1. Start simulation
2. Watch wait times gradually increase
3. Point out bus bunching and overcrowding
4. Highlight rising P90 wait times

**Key Points**:
- "Watch the average wait time climb"
- "Notice buses bunching together"
- "P90 wait time shows 90% of riders wait longer than this"

**Expected Results**:
- Avg wait: 45-60 seconds
- P90 wait: 80-120 seconds
- Load std dev: 8-12 passengers

### Step 3: Switch to RL (90 seconds)
**Objective**: Demonstrate immediate improvement with RL policy

**Actions**:
1. Click "RL Policy" mode switch
2. Watch buses immediately start re-routing
3. Show KPI improvements in real-time
4. Point out the "RL savings" badge on mobile app

**Key Points**:
- "Now switching to our RL-powered dispatcher"
- "Watch buses immediately adapt their routes"
- "The system learns to balance demand across stops"
- "Check the mobile app - riders see their savings"

**Expected Results**:
- Avg wait: 30-40 seconds (20-30% improvement)
- P90 wait: 50-70 seconds
- Load std dev: 5-8 passengers

### Step 4: Road Closure Test (90 seconds)
**Objective**: Test resilience with infrastructure disruption

**Actions**:
1. Click "Road Closure" stress test
2. Show baseline (left map) vs RL (right map) response
3. Watch RL buses find alternative routes
4. Monitor recovery time

**Key Points**:
- "Let's test resilience with a road closure"
- "Watch how RL buses immediately find detours"
- "Baseline buses are stuck, RL buses adapt"
- "Recovery time is under 2 minutes"

**Expected Results**:
- RL recovery: <120 seconds
- Baseline: continues to deteriorate
- Resilience: RL maintains <150% of normal wait times

### Step 5: Demand Surge Test (90 seconds)
**Objective**: Test capacity reallocation during demand spikes

**Actions**:
1. Click "Demand Surge" stress test
2. Show stadium area with sudden high demand
3. Watch RL redirect empty buses
4. Monitor overcrowding control

**Key Points**:
- "Now a demand surge at the stadium"
- "RL immediately redirects empty capacity"
- "Overcrowding stays controlled"
- "Baseline can't respond dynamically"

**Expected Results**:
- RL overcrowding: <30% above normal
- Baseline overcrowding: >100% increase
- Surge handling: RL maintains service levels

### Step 6: Performance Summary (30 seconds)
**Objective**: Highlight final achievements and technical specs

**Actions**:
1. Show final KPI comparison
2. Highlight improvement percentages
3. Display ONNX inference performance
4. Show mobile app rider experience

**Key Points**:
- "Final results show 20-30% improvement"
- "All running locally on Snapdragon X Elite"
- "ONNX inference under 10ms latency"
- "Riders see real-time savings"

**Final Metrics**:
- ΔAvg wait: ≥20% improvement ✓
- Overcrowding: ≥30% reduction ✓
- Resilience: Recovery <120s ✓
- Smoothness: <1 replan per 45s ✓

## Technical Highlights

### Snapdragon X Elite Performance
- **Training**: PPO policy trained offline
- **Inference**: ONNX Runtime on-device
- **Latency**: <10ms per decision
- **Memory**: <100MB model size
- **Throughput**: 100+ FPS simulation

### Architecture
- **Environment**: Custom Gym environment
- **Algorithm**: PPO (Stable Baselines3)
- **Export**: PyTorch → ONNX conversion
- **Server**: FastAPI + WebSocket
- **Frontend**: React dashboard + React Native app

### Real-time Features
- **Live Updates**: 10Hz simulation, 5Hz UI
- **WebSocket**: Bidirectional communication
- **Mobile**: Live bus tracking + ETA
- **Dashboard**: Dual map comparison

## Demo Success Criteria

### Must Achieve
1. **ΔAvg wait**: RL ≥20% lower than baseline
2. **Overcrowding**: ≥30% reduction vs baseline  
3. **Resilience**: Recovery within 120 seconds
4. **Smoothness**: ≤1 replan per 45 seconds
5. **Performance**: Runs entirely on Snapdragon X Elite

### Nice to Have
1. **P90 improvement**: ≥20% reduction
2. **Load balancing**: Lower standard deviation
3. **Mobile experience**: Smooth real-time updates
4. **Visual impact**: Clear bus re-routing

## Troubleshooting

### Common Issues
1. **Server not starting**: Check port 8000 availability
2. **WebSocket disconnect**: Verify firewall settings
3. **Slow performance**: Reduce simulation frequency
4. **Mobile app issues**: Check network connectivity

### Backup Plans
1. **Pre-recorded demo**: Video fallback
2. **Static screenshots**: KPI comparison slides
3. **Local demo**: Run without network dependencies
4. **Simplified version**: Fewer buses/stops for speed

## Post-Demo Discussion

### Technical Questions
- How does the RL policy learn optimal routes?
- What's the training process and data requirements?
- How does ONNX optimize for mobile deployment?
- What are the scalability considerations?

### Business Questions
- How would this scale to real city networks?
- What's the ROI for transit agencies?
- How do you handle real-time disruptions?
- What about passenger safety and reliability?

### Future Enhancements
- Multi-agent coordination
- Real GTFS data integration
- Predictive demand modeling
- Emissions optimization
- Accessibility considerations
