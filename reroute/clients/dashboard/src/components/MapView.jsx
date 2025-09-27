import React from 'react';

function MapView({ data, mode }) {
  const renderGridCell = (x, y, buses, stops) => {
    const cellKey = `${x}-${y}`;
    
    // Find bus at this position
    const bus = buses?.find(b => 
      Math.floor(b.x) === x && Math.floor(b.y) === y
    );
    
    // Find stop at this position
    const stop = stops?.find(s => s.x === x && s.y === y);
    
    let className = 'grid-cell';
    let content = null;
    
    if (bus) {
      className += ' bus';
      content = (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          fontSize: '10px',
          fontWeight: 'bold',
          color: 'white',
          textShadow: '1px 1px 2px rgba(0,0,0,0.7)'
        }}>
          {bus.id}
        </div>
      );
    } else if (stop) {
      className += ' stop';
      
      // Determine demand level
      if (stop.queue_len > 15) {
        className += ' high-demand';
      } else if (stop.queue_len > 5) {
        className += ' medium-demand';
      } else {
        className += ' low-demand';
      }
      
      content = (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          fontSize: '8px',
          fontWeight: 'bold',
          color: 'white',
          textShadow: '1px 1px 2px rgba(0,0,0,0.7)'
        }}>
          {stop.queue_len}
        </div>
      );
    }
    
    return (
      <div key={cellKey} className={className} title={getCellTooltip(x, y, bus, stop)}>
        {content}
      </div>
    );
  };

  const getCellTooltip = (x, y, bus, stop) => {
    if (bus) {
      return `Bus ${bus.id} at (${x}, ${y}) - Load: ${bus.load}/${bus.capacity}`;
    } else if (stop) {
      return `Stop ${stop.id} at (${x}, ${y}) - Queue: ${stop.queue_len} riders`;
    } else {
      return `Position (${x}, ${y})`;
    }
  };

  const renderGrid = () => {
    const grid = [];
    const buses = data?.buses || [];
    const stops = data?.stops || [];
    
    for (let y = 0; y < 20; y++) {
      for (let x = 0; x < 20; x++) {
        grid.push(renderGridCell(x, y, buses, stops));
      }
    }
    
    return grid;
  };

  const getLegendItems = () => [
    { color: '#f59e0b', label: 'Bus', description: 'Vehicle position' },
    { color: '#3b82f6', label: 'Low Demand', description: '≤5 riders' },
    { color: '#f59e0b', label: 'Medium Demand', description: '6-15 riders' },
    { color: '#dc2626', label: 'High Demand', description: '>15 riders' }
  ];

  if (!data) {
    return (
      <div className="map">
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          color: '#6b7280',
          fontSize: '0.9rem'
        }}>
          {mode === 'static' ? 'Waiting for baseline data...' : 'Waiting for RL data...'}
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="map">
        <div className="grid-map">
          {renderGrid()}
        </div>
      </div>
      
      {/* Legend */}
      <div style={{
        marginTop: '0.5rem',
        display: 'flex',
        gap: '1rem',
        flexWrap: 'wrap',
        fontSize: '0.75rem'
      }}>
        {getLegendItems().map((item, index) => (
          <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <div style={{
              width: '12px',
              height: '12px',
              backgroundColor: item.color,
              borderRadius: '50%'
            }}></div>
            <span style={{ fontWeight: '500' }}>{item.label}:</span>
            <span style={{ color: '#6b7280' }}>{item.description}</span>
          </div>
        ))}
      </div>
      
      {/* Stats */}
      <div style={{
        marginTop: '0.5rem',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '0.75rem',
        color: '#6b7280'
      }}>
        <span>Buses: {data.buses?.length || 0}</span>
        <span>Stops: {data.stops?.length || 0}</span>
        <span>Active Riders: {data.kpis?.active_riders || 0}</span>
      </div>
    </div>
  );
}

export default MapView;