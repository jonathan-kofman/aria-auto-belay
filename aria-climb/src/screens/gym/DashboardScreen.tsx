import React, { useMemo, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation } from '@react-navigation/native';
import type { DrawerNavigationProp } from '@react-navigation/drawer';
import type { GymDrawerParamList } from '../../types/navigation';

const DEVICES = [
  { id: 'ARIA-01', wall: 'Lead Wall 1', gradeBand: '5.9–5.11a', state: 'IDLE', activeSessions: 0 },
  { id: 'ARIA-02', wall: 'Lead Wall 2', gradeBand: '5.10b–5.11d', state: 'CLIMBING', activeSessions: 1 },
  { id: 'ARIA-03', wall: 'Training Wall', gradeBand: '5.7–5.10a', state: 'CLIMBING_PAUSED', activeSessions: 1 },
];

type Nav = DrawerNavigationProp<GymDrawerParamList, 'Dashboard'>;

export function DashboardScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<Nav>();
  const [filter, setFilter] = useState<'all' | 'active' | 'paused'>('all');

  const totalDevices = DEVICES.length;
  const active = DEVICES.filter((d) => d.state === 'CLIMBING').length;
  const paused = DEVICES.filter((d) => d.state === 'CLIMBING_PAUSED').length;
  const filteredDevices = useMemo(() => {
    if (filter === 'active') return DEVICES.filter((d) => d.state === 'CLIMBING');
    if (filter === 'paused') return DEVICES.filter((d) => d.state === 'CLIMBING_PAUSED');
    return DEVICES;
  }, [filter]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('gym.dashboard')}</Text>
      <Text style={styles.subtitle}>Overview for tonight</Text>

      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Devices</Text>
          <Text style={styles.summaryValue}>{totalDevices}</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Active</Text>
          <Text style={styles.summaryValue}>{active}</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Paused</Text>
          <Text style={styles.summaryValue}>{paused}</Text>
        </View>
      </View>

      <View style={styles.filterRow}>
        <TouchableOpacity
          style={[styles.filterChip, filter === 'all' && styles.filterChipActive]}
          onPress={() => setFilter('all')}
        >
          <Text style={filter === 'all' ? styles.filterTextActive : styles.filterText}>All</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterChip, filter === 'active' && styles.filterChipActive]}
          onPress={() => setFilter('active')}
        >
          <Text style={filter === 'active' ? styles.filterTextActive : styles.filterText}>Active</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.filterChip, filter === 'paused' && styles.filterChipActive]}
          onPress={() => setFilter('paused')}
        >
          <Text style={filter === 'paused' ? styles.filterTextActive : styles.filterText}>Paused</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={filteredDevices}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.deviceCard}
            onPress={() => navigation.navigate('DeviceDetail', { deviceId: item.id })}
          >
            <Text style={styles.deviceId}>{item.id}</Text>
            <Text style={styles.deviceLine}>{item.wall}</Text>
            <Text style={styles.deviceLine}>Routes: {item.gradeBand}</Text>
            <Text style={styles.deviceLine}>
              State: {item.state} · Active sessions: {item.activeSessions}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 4 },
  subtitle: { color: '#666', marginBottom: 16 },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  summaryCard: {
    flex: 1,
    marginHorizontal: 4,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: '#1a1a2e',
    alignItems: 'center',
  },
  summaryLabel: { color: '#ccc', fontSize: 12 },
  summaryValue: { color: '#fff', fontSize: 18, fontWeight: '600' },
  filterRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    marginBottom: 8,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#ccc',
    marginRight: 8,
  },
  filterChipActive: {
    backgroundColor: '#1a1a2e',
    borderColor: '#1a1a2e',
  },
  filterText: { color: '#333', fontSize: 12 },
  filterTextActive: { color: '#fff', fontSize: 12, fontWeight: '600' },
  deviceCard: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    marginBottom: 12,
    backgroundColor: '#fff',
  },
  deviceId: { fontSize: 16, fontWeight: '600', marginBottom: 4 },
  deviceLine: { color: '#444', marginBottom: 2 },
});
