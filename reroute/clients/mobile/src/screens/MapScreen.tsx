import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
} from 'react-native';
import { useWebSocket } from '../context/WebSocketContext';
import { MapPin, Bus, Users, RefreshCw, Navigation } from 'react-native-vector-icons/MaterialIcons';

// Mock map component - in a real app, you'd use react-native-maps
const MockMap: React.FC<{
  buses: any[];
  stops: any[];
  onStopPress: (stop: any) => void;
  onBusPress: (bus: any) => void;
}> = ({ buses, stops, onStopPress, onBusPress }) => {
  const { width } = Dimensions.get('window');
  const mapSize = width - 40; // Account for padding
  const cellSize = mapSize / 20; // 20x20 grid

  const getCellStyle = (x: number, y: number) => ({
    position: 'absolute' as const,
    left: x * cellSize,
    top: y * cellSize,
    width: cellSize,
    height: cellSize,
    backgroundColor: '#f3f4f6',
    borderWidth: 0.5,
    borderColor: '#d1d5db',
  });

  const getStopStyle = (stop: any) => {
    const demandColor = stop.queue_len > 15 ? '#ef4444' : stop.queue_len > 5 ? '#f59e0b' : '#10b981';
    return {
      position: 'absolute' as const,
      left: stop.x * cellSize + cellSize / 4,
      top: stop.y * cellSize + cellSize / 4,
      width: cellSize / 2,
      height: cellSize / 2,
      backgroundColor: demandColor,
      borderRadius: cellSize / 4,
      justifyContent: 'center' as const,
      alignItems: 'center' as const,
    };
  };

  const getBusStyle = (bus: any) => ({
    position: 'absolute' as const,
    left: bus.x * cellSize + cellSize / 3,
    top: bus.y * cellSize + cellSize / 3,
    width: cellSize / 3,
    height: cellSize / 3,
    backgroundColor: '#3b82f6',
    borderRadius: cellSize / 6,
    justifyContent: 'center' as const,
    alignItems: 'center' as const,
  });

  return (
    <View style={[styles.mockMap, { width: mapSize, height: mapSize }]}>
      {/* Grid cells */}
      {Array.from({ length: 400 }, (_, i) => {
        const x = i % 20;
        const y = Math.floor(i / 20);
        return <View key={i} style={getCellStyle(x, y)} />;
      })}
      
      {/* Stops */}
      {stops.map((stop) => (
        <TouchableOpacity
          key={`stop-${stop.id}`}
          style={getStopStyle(stop)}
          onPress={() => onStopPress(stop)}
        >
          <Text style={styles.stopText}>{stop.id}</Text>
        </TouchableOpacity>
      ))}
      
      {/* Buses */}
      {buses.map((bus) => (
        <TouchableOpacity
          key={`bus-${bus.id}`}
          style={getBusStyle(bus)}
          onPress={() => onBusPress(bus)}
        >
          <Text style={styles.busText}>{bus.id}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
};

const MapScreen: React.FC = () => {
  const { simulationData } = useWebSocket();
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [showLegend, setShowLegend] = useState(true);

  const buses = simulationData?.buses || [];
  const stops = simulationData?.stops || [];

  const handleStopPress = (stop: any) => {
    setSelectedItem({
      type: 'stop',
      data: stop,
    });
  };

  const handleBusPress = (bus: any) => {
    setSelectedItem({
      type: 'bus',
      data: bus,
    });
  };

  const getDemandLevel = (queueLen: number): { level: string; color: string } => {
    if (queueLen <= 5) return { level: 'Low', color: '#10b981' };
    if (queueLen <= 15) return { level: 'Medium', color: '#f59e0b' };
    return { level: 'High', color: '#ef4444' };
  };

  const getCapacityStatus = (load: number, capacity: number): { status: string; color: string } => {
    const ratio = load / capacity;
    if (ratio < 0.5) return { status: 'Available', color: '#10b981' };
    if (ratio < 0.8) return { status: 'Busy', color: '#f59e0b' };
    return { status: 'Full', color: '#ef4444' };
  };

  const refreshMap = () => {
    setSelectedItem(null);
    // Force re-render
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>Live Map</Text>
          <Text style={styles.headerSubtitle}>
            {buses.length} buses • {stops.length} stops
          </Text>
        </View>
        <TouchableOpacity style={styles.refreshButton} onPress={refreshMap}>
          <RefreshCw size={20} color="#3b82f6" />
        </TouchableOpacity>
      </View>

      {/* Map */}
      <View style={styles.mapContainer}>
        <MockMap
          buses={buses}
          stops={stops}
          onStopPress={handleStopPress}
          onBusPress={handleBusPress}
        />
      </View>

      {/* Legend */}
      {showLegend && (
        <View style={styles.legend}>
          <View style={styles.legendHeader}>
            <Text style={styles.legendTitle}>Legend</Text>
            <TouchableOpacity onPress={() => setShowLegend(false)}>
              <Text style={styles.legendToggle}>Hide</Text>
            </TouchableOpacity>
          </View>
          
          <View style={styles.legendItems}>
            <View style={styles.legendItem}>
              <View style={[styles.legendColor, { backgroundColor: '#3b82f6' }]} />
              <Text style={styles.legendLabel}>Bus</Text>
            </View>
            
            <View style={styles.legendItem}>
              <View style={[styles.legendColor, { backgroundColor: '#10b981' }]} />
              <Text style={styles.legendLabel}>Low Demand</Text>
            </View>
            
            <View style={styles.legendItem}>
              <View style={[styles.legendColor, { backgroundColor: '#f59e0b' }]} />
              <Text style={styles.legendLabel}>Medium Demand</Text>
            </View>
            
            <View style={styles.legendItem}>
              <View style={[styles.legendColor, { backgroundColor: '#ef4444' }]} />
              <Text style={styles.legendLabel}>High Demand</Text>
            </View>
          </View>
        </View>
      )}

      {!showLegend && (
        <TouchableOpacity style={styles.showLegendButton} onPress={() => setShowLegend(true)}>
          <Text style={styles.showLegendText}>Show Legend</Text>
        </TouchableOpacity>
      )}

      {/* Selected Item Details */}
      {selectedItem && (
        <View style={styles.detailsPanel}>
          <View style={styles.detailsHeader}>
            <Text style={styles.detailsTitle}>
              {selectedItem.type === 'stop' ? 'Stop' : 'Bus'} #{selectedItem.data.id}
            </Text>
            <TouchableOpacity onPress={() => setSelectedItem(null)}>
              <Text style={styles.closeButton}>✕</Text>
            </TouchableOpacity>
          </View>
          
          {selectedItem.type === 'stop' ? (
            <View style={styles.detailsContent}>
              <View style={styles.detailRow}>
                <MapPin size={16} color="#6b7280" />
                <Text style={styles.detailLabel}>Position:</Text>
                <Text style={styles.detailValue}>({selectedItem.data.x}, {selectedItem.data.y})</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Users size={16} color="#6b7280" />
                <Text style={styles.detailLabel}>Queue:</Text>
                <Text style={styles.detailValue}>{selectedItem.data.queue_len} riders</Text>
              </View>
              
              <View style={styles.detailRow}>
                <View style={[
                  styles.demandIndicator,
                  { backgroundColor: getDemandLevel(selectedItem.data.queue_len).color }
                ]} />
                <Text style={styles.detailLabel}>Demand:</Text>
                <Text style={styles.detailValue}>{getDemandLevel(selectedItem.data.queue_len).level}</Text>
              </View>
              
              <TouchableOpacity style={styles.actionButton}>
                <Navigation size={16} color="#ffffff" />
                <Text style={styles.actionButtonText}>Get Directions</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.detailsContent}>
              <View style={styles.detailRow}>
                <Bus size={16} color="#6b7280" />
                <Text style={styles.detailLabel}>Position:</Text>
                <Text style={styles.detailValue}>({selectedItem.data.x.toFixed(1)}, {selectedItem.data.y.toFixed(1)})</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Users size={16} color="#6b7280" />
                <Text style={styles.detailLabel}>Load:</Text>
                <Text style={styles.detailValue}>{selectedItem.data.load}/{selectedItem.data.capacity}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <View style={[
                  styles.capacityIndicator,
                  { backgroundColor: getCapacityStatus(selectedItem.data.load, selectedItem.data.capacity).color }
                ]} />
                <Text style={styles.detailLabel}>Status:</Text>
                <Text style={styles.detailValue}>{getCapacityStatus(selectedItem.data.load, selectedItem.data.capacity).status}</Text>
              </View>
              
              <TouchableOpacity style={styles.actionButton}>
                <Bus size={16} color="#ffffff" />
                <Text style={styles.actionButtonText}>Track Bus</Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      )}

      {/* Status Bar */}
      <View style={styles.statusBar}>
        <View style={styles.statusItem}>
          <Bus size={16} color="#3b82f6" />
          <Text style={styles.statusText}>{buses.length} Active</Text>
        </View>
        <View style={styles.statusItem}>
          <MapPin size={16} color="#10b981" />
          <Text style={styles.statusText}>{stops.length} Stops</Text>
        </View>
        <View style={styles.statusItem}>
          <Users size={16} color="#f59e0b" />
          <Text style={styles.statusText}>
            {simulationData?.kpis?.active_riders || 0} Riders
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1e293b',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 2,
  },
  refreshButton: {
    padding: 8,
  },
  mapContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  mockMap: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    position: 'relative',
  },
  stopText: {
    fontSize: 8,
    fontWeight: 'bold',
    color: '#ffffff',
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 1,
  },
  busText: {
    fontSize: 8,
    fontWeight: 'bold',
    color: '#ffffff',
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 1,
  },
  legend: {
    backgroundColor: '#ffffff',
    margin: 20,
    borderRadius: 8,
    padding: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  legendHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  legendTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
  },
  legendToggle: {
    fontSize: 14,
    color: '#3b82f6',
    fontWeight: '500',
  },
  legendItems: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  legendLabel: {
    fontSize: 12,
    color: '#6b7280',
  },
  showLegendButton: {
    backgroundColor: '#ffffff',
    margin: 20,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    alignItems: 'center',
  },
  showLegendText: {
    fontSize: 14,
    color: '#3b82f6',
    fontWeight: '500',
  },
  detailsPanel: {
    backgroundColor: '#ffffff',
    margin: 20,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    maxHeight: 300,
  },
  detailsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  detailsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
  },
  closeButton: {
    fontSize: 18,
    color: '#6b7280',
    padding: 4,
  },
  detailsContent: {
    padding: 16,
    gap: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  detailLabel: {
    fontSize: 14,
    color: '#6b7280',
    minWidth: 60,
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1e293b',
    flex: 1,
  },
  demandIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  capacityIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#3b82f6',
    padding: 12,
    borderRadius: 6,
    marginTop: 8,
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#ffffff',
  },
  statusBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statusText: {
    fontSize: 12,
    color: '#6b7280',
    fontWeight: '500',
  },
});

export default MapScreen;