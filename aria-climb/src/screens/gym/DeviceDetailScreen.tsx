import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useRoute, RouteProp, useNavigation } from '@react-navigation/native';
import firestore from '@react-native-firebase/firestore';
import type { GymDrawerParamList } from '../../types/navigation';
import { StateMachineViz } from '../../components/gym/StateMachineViz';
import { useAuthStore } from '../../store/authStore';
import { useARIADevice } from '../../hooks/useARIADevice';
import { issueCommand } from '../../services/firebase/ariaDevice';

const DEVICES = [
  {
    id: 'ARIA-01',
    wall: 'Lead Wall 1',
    lastInspection: 'Feb 10, 2026',
    state: 'IDLE',
    currentRoute: '5.10c – Warmup arete',
  },
  {
    id: 'ARIA-02',
    wall: 'Lead Wall 2',
    lastInspection: 'Feb 20, 2026',
    state: 'CLIMBING',
    currentRoute: '5.11b – Techy face',
  },
];

export function DeviceDetailScreen() {
  const route = useRoute<RouteProp<GymDrawerParamList, 'DeviceDetail'>>();
  const navigation = useNavigation();
  const { deviceId } = route.params;

  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';
  const { device, isLoading } = useARIADevice(gymId, deviceId);

  const fallback = DEVICES.find((d) => d.id === deviceId);
  const [maintenanceLocked, setMaintenanceLocked] = useState(false);
  const [motorPaused, setMotorPaused] = useState(false);

  const effective = device
    ? {
        id: device.deviceId,
        wall: device.wallName,
        state: device.state,
        currentRoute: device.gradeBand,
        lastInspection: device.lastMaintenanceAt
          ? device.lastMaintenanceAt.toLocaleDateString()
          : '—',
      }
    : fallback;

  if (isLoading && !effective) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Loading device…</Text>
      </View>
    );
  }

  if (!effective) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Device not found</Text>
        <Text style={styles.line}>ID: {deviceId}</Text>
      </View>
    );
  }

  async function sendCommand(cmd: 'PAUSE_MOTOR' | 'RESUME_MOTOR' | 'LOCKOUT' | 'RETURN_TO_SERVICE') {
    if (!user) return;
    try {
      await issueCommand({
        deviceId,
        gymId,
        command: cmd,
        params: {},
        issuedBy: user.uid,
        issuedByName: user.displayName,
        issuedAt: firestore.Timestamp.now() as any,
      });
    } catch {
      // swallow in UI for now; could show toast later
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{effective.id}</Text>
      <Text style={styles.line}>{effective.wall}</Text>
      <Text style={styles.line}>
        State:{' '}
        {maintenanceLocked
          ? 'MAINTENANCE'
          : motorPaused
          ? 'REST'
          : device?.state ?? effective.state}
      </Text>
      <Text style={styles.line}>Current route: {effective.currentRoute}</Text>
      <Text style={styles.line}>Last inspection: {effective.lastInspection}</Text>

      {maintenanceLocked && (
        <Text style={styles.warning}>
          ARIA is locked out for maintenance. Climbs are blocked until returned to service.
        </Text>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Maintenance controls</Text>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.controlButton, motorPaused && styles.controlButtonActive]}
            onPress={() => {
              setMotorPaused(true);
              void sendCommand('PAUSE_MOTOR');
            }}
          >
            <Text style={styles.controlButtonText}>Pause motor</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.controlButton, !motorPaused && styles.controlButtonActive]}
            onPress={() => {
              setMotorPaused(false);
              void sendCommand('RESUME_MOTOR');
            }}
          >
            <Text style={styles.controlButtonText}>Resume motor</Text>
          </TouchableOpacity>
        </View>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.controlButton, maintenanceLocked && styles.dangerButtonActive]}
            onPress={() => {
              setMaintenanceLocked(true);
              void sendCommand('LOCKOUT');
            }}
          >
            <Text style={styles.controlButtonText}>Lock out for maintenance</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.controlButton, !maintenanceLocked && styles.controlButtonActive]}
            onPress={() => {
              setMaintenanceLocked(false);
              void sendCommand('RETURN_TO_SERVICE');
            }}
          >
            <Text style={styles.controlButtonText}>Return to service</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Live state</Text>
        <StateMachineViz deviceId={effective.id} />
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Health & inspections</Text>
        <TouchableOpacity
          style={[styles.controlButton, styles.controlButtonActive]}
          onPress={() =>
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (navigation as any).navigate('DeviceHealth', { deviceId: effective.id })
          }
        >
          <Text style={styles.controlButtonText}>View device health</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 8 },
  line: { color: '#444', marginBottom: 4 },
  warning: { color: '#b91c1c', marginTop: 4, marginBottom: 4 },
  card: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 16,
    marginTop: 16,
    backgroundColor: '#fff',
  },
  cardTitle: { fontSize: 18, marginBottom: 8 },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  controlButton: {
    flex: 1,
    marginHorizontal: 4,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ccc',
    alignItems: 'center',
  },
  controlButtonActive: {
    backgroundColor: '#1a1a2e',
    borderColor: '#1a1a2e',
  },
  dangerButtonActive: {
    backgroundColor: '#b91c1c',
    borderColor: '#b91c1c',
  },
  controlButtonText: { color: '#fff', fontSize: 12 },
});
