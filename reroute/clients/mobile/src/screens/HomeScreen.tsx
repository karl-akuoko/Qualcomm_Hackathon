import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  RefreshControl,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Bus, MapPin, Clock, TrendingUp, Wifi, WifiOff } from 'react-native-vector-icons/MaterialIcons';
import { useWebSocket } from '../context/WebSocketContext';

interface Stop {
  id: number;
  x: number;
  y: number;
  queue_len: number;
}

interface Bus {
  id: number;
  x: number;
  y: number;
  load: number;
  capacity: number;
}

const HomeScreen: React.FC = () => {
  const navigation = useNavigation();
  const { isConnected, simulationData, error } = useWebSocket();
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = React.useCallback(() => {
    setRefreshing(true);
    // Simulate refresh
    setTimeout(() => {
      setRefreshing(false);
    }, 1000);
  }, []);

  const calculateETA = (bus: Bus, stop: Stop): number => {
    // Simple distance-based ETA calculation
    const distance = Math.sqrt(Math.pow(bus.x - stop.x, 2) + Math.pow(bus.y - stop.y, 2));
    return Math.round(distance * 30); // 30 seconds per grid unit
  };

  const getNearbyBuses = (stop: Stop): Array<Bus & { eta: number }> => {
    if (!simulationData?.buses) return [];

    return simulationData.buses
      .map(bus => ({
        ...bus,
        eta: calculateETA(bus, stop)
      }))
      .filter(bus => bus.eta <= 600) // Within 10 minutes
      .sort((a, b) => a.eta - b.eta)
      .slice(0, 3); // Top 3 buses
  };

  const getDemandLevel = (queueLen: number): { level: string; color: string } => {
    if (queueLen <= 5) return { level: 'Low', color: '#10b981' };
    if (queueLen <= 15) return { level: 'Medium', color: '#f59e0b' };
    return { level: 'High', color: '#ef4444' };
  };

  const getRlSavings = (): { improvement: number; status: string } => {
    // Mock RL savings calculation
    const avgWait = simulationData?.kpis?.avg_wait || 0;
    if (avgWait > 0) {
      const improvement = Math.min(25, Math.max(5, 30 - avgWait * 2));
      return {
        improvement,
        status: improvement > 15 ? 'active' : 'limited'
      };
    }
    return { improvement: 0, status: 'inactive' };
  };

  const rlSavings = getRlSavings();

  if (!simulationData) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>🚌 Bus Tracker</Text>
          <View style={styles.connectionStatus}>
            {isConnected ? (
              <Wifi size={20} color="#10b981" />
            ) : (
              <WifiOff size={20} color="#ef4444" />
            )}
            <Text style={[styles.connectionText, { color: isConnected ? '#10b981' : '#ef4444' }]}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </Text>
          </View>
        </View>
        
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>
            {error || 'Connecting to simulation...'}
          </Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🚌 Bus Tracker</Text>
        <View style={styles.connectionStatus}>
          {isConnected ? (
            <Wifi size={20} color="#10b981" />
          ) : (
            <WifiOff size={20} color="#ef4444" />
          )}
          <Text style={[styles.connectionText, { color: isConnected ? '#10b981' : '#ef4444' }]}>
            {isConnected ? 'Live' : 'Offline'}
          </Text>
        </View>
      </View>

      {/* RL Savings Badge */}
      {rlSavings.improvement > 0 && (
        <View style={[styles.savingsBadge, { backgroundColor: rlSavings.status === 'active' ? '#dcfce7' : '#fef3c7' }]}>
          <TrendingUp size={16} color={rlSavings.status === 'active' ? '#166534' : '#92400e'} />
          <Text style={[styles.savingsText, { color: rlSavings.status === 'active' ? '#166534' : '#92400e' }]}>
            RL Mode: {rlSavings.improvement.toFixed(1)}% faster service
          </Text>
        </View>
      )}

      {/* Quick Stats */}
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Bus size={24} color="#3b82f6" />
          <Text style={styles.statNumber}>{simulationData.buses?.length || 0}</Text>
          <Text style={styles.statLabel}>Active Buses</Text>
        </View>
        <View style={styles.statCard}>
          <MapPin size={24} color="#10b981" />
          <Text style={styles.statNumber}>{simulationData.stops?.length || 0}</Text>
          <Text style={styles.statLabel}>Stops</Text>
        </View>
        <View style={styles.statCard}>
          <Clock size={24} color="#f59e0b" />
          <Text style={styles.statNumber}>
            {simulationData.kpis?.avg_wait ? simulationData.kpis.avg_wait.toFixed(1) : '0'}
          </Text>
          <Text style={styles.statLabel}>Avg Wait (s)</Text>
        </View>
      </View>

      {/* Bus Stops */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Nearby Stops</Text>
        {simulationData.stops?.slice(0, 10).map((stop) => {
          const nearbyBuses = getNearbyBuses(stop);
          const demand = getDemandLevel(stop.queue_len);
          
          return (
            <TouchableOpacity
              key={stop.id}
              style={styles.stopCard}
              onPress={() => navigation.navigate('StopDetail', { stopId: stop.id })}
            >
              <View style={styles.stopHeader}>
                <View style={styles.stopInfo}>
                  <Text style={styles.stopName}>Stop #{stop.id}</Text>
                  <View style={styles.stopLocation}>
                    <MapPin size={14} color="#6b7280" />
                    <Text style={styles.locationText}>Grid ({stop.x}, {stop.y})</Text>
                  </View>
                </View>
                <View style={[styles.demandBadge, { backgroundColor: demand.color + '20' }]}>
                  <Text style={[styles.demandText, { color: demand.color }]}>
                    {demand.level}
                  </Text>
                </View>
              </View>
              
              <View style={styles.stopDetails}>
                <View style={styles.queueInfo}>
                  <Text style={styles.queueLabel}>Queue:</Text>
                  <Text style={styles.queueValue}>{stop.queue_len} riders</Text>
                </View>
                
                {nearbyBuses.length > 0 && (
                  <View style={styles.etaInfo}>
                    <Text style={styles.etaLabel}>Next buses:</Text>
                    {nearbyBuses.map((bus, index) => (
                      <View key={bus.id} style={styles.etaItem}>
                        <Bus size={12} color="#3b82f6" />
                        <Text style={styles.etaText}>
                          Bus {bus.id} - {Math.floor(bus.eta / 60)}:{(bus.eta % 60).toString().padStart(2, '0')}
                        </Text>
                        <View style={[styles.capacityIndicator, { 
                          backgroundColor: bus.load / bus.capacity > 0.8 ? '#ef4444' : '#10b981' 
                        }]} />
                      </View>
                    ))}
                  </View>
                )}
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => navigation.navigate('Map')}
        >
          <MapPin size={20} color="#3b82f6" />
          <Text style={styles.actionButtonText}>View Live Map</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
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
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
  },
  connectionStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  connectionText: {
    fontSize: 14,
    fontWeight: '500',
  },
  savingsBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    margin: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  savingsText: {
    fontSize: 14,
    fontWeight: '600',
  },
  statsContainer: {
    flexDirection: 'row',
    padding: 16,
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  statNumber: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1e293b',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginTop: 4,
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 12,
  },
  stopCard: {
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 8,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  stopHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  stopInfo: {
    flex: 1,
  },
  stopName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
  },
  stopLocation: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 4,
  },
  locationText: {
    fontSize: 12,
    color: '#6b7280',
  },
  demandBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  demandText: {
    fontSize: 12,
    fontWeight: '600',
  },
  stopDetails: {
    gap: 8,
  },
  queueInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  queueLabel: {
    fontSize: 14,
    color: '#6b7280',
  },
  queueValue: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1e293b',
  },
  etaInfo: {
    gap: 4,
  },
  etaLabel: {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 4,
  },
  etaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  etaText: {
    fontSize: 12,
    color: '#1e293b',
    flex: 1,
  },
  capacityIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#3b82f6',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
  },
});

export default HomeScreen;