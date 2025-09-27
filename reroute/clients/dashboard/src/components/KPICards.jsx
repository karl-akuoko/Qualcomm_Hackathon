import React from 'react';
import { TrendingUp, TrendingDown, Clock, Users, AlertTriangle } from 'lucide-react';

function KPICards({ baselineKPIs, rlKPIs, currentKPIs, mode }) {
  const calculateImprovement = (baseline, rl) => {
    if (!baseline || baseline === 0) return 0;
    return ((baseline - rl) / baseline) * 100;
  };

  const getKPIValue = (kpiData, key) => {
    return kpiData?.[key] || 0;
  };

  const formatValue = (value, decimals = 2) => {
    return typeof value === 'number' ? value.toFixed(decimals) : '0.00';
  };

  const getImprovementColor = (improvement) => {
    if (improvement > 0) return 'positive';
    if (improvement < 0) return 'negative';
    return '';
  };

  const getImprovementIcon = (improvement) => {
    if (improvement > 0) return <TrendingUp size={12} />;
    if (improvement < 0) return <TrendingDown size={12} />;
    return null;
  };

  const kpiCards = [
    {
      key: 'avg_wait',
      title: 'Average Wait Time',
      unit: 'seconds',
      icon: <Clock size={16} />,
      baseline: getKPIValue(baselineKPIs, 'avg_wait'),
      rl: getKPIValue(rlKPIs, 'avg_wait'),
      current: getKPIValue(currentKPIs, 'avg_wait'),
      target: '≥20% improvement'
    },
    {
      key: 'p90_wait',
      title: '90th Percentile Wait',
      unit: 'seconds',
      icon: <Clock size={16} />,
      baseline: getKPIValue(baselineKPIs, 'p90_wait'),
      rl: getKPIValue(rlKPIs, 'p90_wait'),
      current: getKPIValue(currentKPIs, 'p90_wait'),
      target: '≥20% improvement'
    },
    {
      key: 'load_std',
      title: 'Load Standard Deviation',
      unit: 'passengers',
      icon: <Users size={16} />,
      baseline: getKPIValue(baselineKPIs, 'load_std'),
      rl: getKPIValue(rlKPIs, 'load_std'),
      current: getKPIValue(currentKPIs, 'load_std'),
      target: 'Lower is better'
    },
    {
      key: 'overcrowd_ratio',
      title: 'Overcrowding Ratio',
      unit: '%',
      icon: <AlertTriangle size={16} />,
      baseline: getKPIValue(baselineKPIs, 'overcrowd_ratio') * 100,
      rl: getKPIValue(rlKPIs, 'overcrowd_ratio') * 100,
      current: getKPIValue(currentKPIs, 'overcrowd_ratio') * 100,
      target: '≥30% reduction'
    },
    {
      key: 'replan_frequency',
      title: 'Replan Frequency',
      unit: 'per hour',
      icon: <TrendingUp size={16} />,
      baseline: getKPIValue(baselineKPIs, 'replan_frequency'),
      rl: getKPIValue(rlKPIs, 'replan_frequency'),
      current: getKPIValue(currentKPIs, 'replan_frequency'),
      target: '≤1 per 45s'
    }
  ];

  const renderKPI = (kpi) => {
    const improvement = calculateImprovement(kpi.baseline, kpi.rl);
    const currentValue = mode === 'static' ? kpi.baseline : (mode === 'rl' ? kpi.rl : kpi.current);
    
    return (
      <div key={kpi.key} className="kpi-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          {kpi.icon}
          <h4>{kpi.title}</h4>
        </div>
        
        <div className="value">
          {formatValue(currentValue)}
        </div>
        
        <div className="unit">
          {kpi.unit}
        </div>
        
        {kpi.baseline > 0 && kpi.rl > 0 && (
          <div className={`improvement ${getImprovementColor(improvement)}`}>
            {getImprovementIcon(improvement)}
            {improvement > 0 ? '+' : ''}{formatValue(improvement, 1)}%
          </div>
        )}
        
        <div style={{ 
          fontSize: '0.7rem', 
          color: '#9ca3af', 
          marginTop: '0.5rem',
          fontStyle: 'italic'
        }}>
          Target: {kpi.target}
        </div>
      </div>
    );
  };

  const getOverallImprovement = () => {
    if (!baselineKPIs.avg_wait || !rlKPIs.avg_wait) return null;
    
    const avgWaitImprovement = calculateImprovement(baselineKPIs.avg_wait, rlKPIs.avg_wait);
    const p90WaitImprovement = calculateImprovement(baselineKPIs.p90_wait, rlKPIs.p90_wait);
    
    return (avgWaitImprovement + p90WaitImprovement) / 2;
  };

  const overallImprovement = getOverallImprovement();

  return (
    <div className="kpi-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>Key Performance Indicators</h3>
        {overallImprovement && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '20px',
            backgroundColor: overallImprovement > 20 ? '#dcfce7' : '#fef3c7',
            color: overallImprovement > 20 ? '#166534' : '#92400e',
            fontSize: '0.9rem',
            fontWeight: '600'
          }}>
            {overallImprovement > 20 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            Overall: {formatValue(overallImprovement, 1)}% improvement
          </div>
        )}
      </div>
      
      <div className="kpi-grid">
        {kpiCards.map(renderKPI)}
      </div>
      
      {/* Success Criteria Status */}
      <div style={{
        marginTop: '1rem',
        padding: '1rem',
        backgroundColor: '#f8fafc',
        borderRadius: '6px',
        border: '1px solid #e2e8f0'
      }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: '600', marginBottom: '0.5rem', color: '#374151' }}>
          MVP Success Criteria
        </h4>
        <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <div>
              ✓ ΔAvg wait: RL ≥20% lower than baseline
            </div>
            <div>
              ✓ Overcrowding: ≥30% lower vs baseline
            </div>
            <div>
              ✓ Resilience: Recovery within 120s
            </div>
            <div>
              ✓ Smoothness: ≤1 replan per 45s
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default KPICards;