import React, { useMemo, useState } from 'react';
import { View, Text, FlatList, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';

const ALERTS = [
  {
    id: 'a1',
    time: '20:14',
    deviceId: 'ARIA-03',
    type: 'zone_intrusion',
    message: 'Fall zone occupied during climb',
    severity: 'high',
  },
  {
    id: 'a2',
    time: '19:52',
    deviceId: 'ARIA-02',
    type: 'fall_detected',
    message: 'Hard fall detected, motor paused',
    severity: 'medium',
  },
  {
    id: 'a3',
    time: '19:30',
    deviceId: 'ARIA-01',
    type: 'device_offline',
    message: 'Device briefly disconnected, auto-recovered',
    severity: 'low',
  },
];

export function AlertHistoryScreen() {
  const { t } = useTranslation();
  const [severityFilter, setSeverityFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const filteredAlerts = useMemo(() => {
    if (severityFilter === 'all') return ALERTS;
    return ALERTS.filter((a) => a.severity === severityFilter);
  }, [severityFilter]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('gym.alerts')}</Text>
      <View style={styles.filterRow}>
        {(['all', 'high', 'medium', 'low'] as const).map((key) => (
          <TouchableOpacity
            key={key}
            style={[styles.filterChip, severityFilter === key && styles.filterChipActive]}
            onPress={() => setSeverityFilter(key)}
          >
            <Text
              style={severityFilter === key ? styles.filterTextActive : styles.filterText}
            >
              {key.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      <FlatList
        data={filteredAlerts}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View style={styles.timeCol}>
              <Text style={styles.time}>{item.time}</Text>
              <Text style={[styles.badge, styles[`badge_${item.severity}` as const]]}>
                {item.severity.toUpperCase()}
              </Text>
            </View>
            <View style={styles.info}>
              <Text style={styles.device}>{item.deviceId}</Text>
              <Text style={styles.message}>{item.message}</Text>
              <Text style={styles.type}>{item.type}</Text>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 12 },
  filterRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  filterChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#ccc',
    marginRight: 6,
  },
  filterChipActive: {
    backgroundColor: '#1a1a2e',
    borderColor: '#1a1a2e',
  },
  filterText: { fontSize: 10, color: '#333' },
  filterTextActive: { fontSize: 10, color: '#fff', fontWeight: '600' },
  row: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  timeCol: { width: 70, alignItems: 'flex-start' },
  time: { fontSize: 14, color: '#222' },
  badge: {
    marginTop: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    fontSize: 10,
    overflow: 'hidden',
    color: '#fff',
  },
  badge_high: { backgroundColor: '#b91c1c' },
  badge_medium: { backgroundColor: '#d97706' },
  badge_low: { backgroundColor: '#15803d' },
  info: { flex: 1, paddingLeft: 8 },
  device: { fontSize: 14, fontWeight: '500' },
  message: { fontSize: 12, color: '#222', marginTop: 2 },
  type: { fontSize: 11, color: '#666', marginTop: 2 },
});
