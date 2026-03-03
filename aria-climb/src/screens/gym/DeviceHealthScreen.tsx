import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import firestore from '@react-native-firebase/firestore';
import type { GymDrawerParamList } from '../../types/navigation';
import { useAuthStore } from '../../store/authStore';
import { useARIADevice } from '../../hooks/useARIADevice';
import type { MaintenanceAction } from '../../types/aria';

type DeviceHealthRoute = RouteProp<GymDrawerParamList, 'DeviceHealth'>;

type MaintenanceLog = {
  id: string;
  action: MaintenanceAction;
  performedByName: string;
  timestamp: Date;
  notes: string;
};

export function DeviceHealthScreen() {
  const route = useRoute<DeviceHealthRoute>();
  const { deviceId } = route.params;
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';

  const { device, isLoading } = useARIADevice(gymId, deviceId);
  const [logs, setLogs] = useState<MaintenanceLog[]>([]);
  const [logNotes, setLogNotes] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!gymId) return;
    const path = `gyms/${gymId}/devices/${deviceId}/maintenanceLogs`;
    const unsub = firestore()
      .collection(path)
      .orderBy('timestamp', 'desc')
      .limit(20)
      .onSnapshot((snap) => {
        const next: MaintenanceLog[] = snap.docs.map((d) => {
          const data = d.data() as any;
          return {
            id: d.id,
            action: data.action as MaintenanceAction,
            performedByName: data.performedByName ?? data.performedBy ?? 'Unknown',
            timestamp: data.timestamp?.toDate
              ? data.timestamp.toDate()
              : new Date(),
            notes: data.notes ?? '',
          };
        });
        setLogs(next);
      });
    return unsub;
  }, [gymId, deviceId]);

  const daysUntilInspection =
    device && device.nextInspectionDue
      ? Math.max(
          0,
          Math.round(
            (device.nextInspectionDue.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
          )
        )
      : null;

  const lastLog = logs[0];

  async function handleLogInspection() {
    if (!user || !gymId) return;
    setSaving(true);
    try {
      const path = `gyms/${gymId}/devices/${deviceId}/maintenanceLogs`;
      const ref = firestore().collection(path).doc();
      await ref.set({
        logId: ref.id,
        gymId,
        deviceId,
        action: 'INSPECTION',
        performedBy: user.uid,
        performedByName: user.displayName ?? user.email ?? 'Unknown',
        timestamp: firestore.Timestamp.now(),
        notes: logNotes,
        firmwareVersionBefore: device?.firmwareVersion ?? null,
        firmwareVersionAfter: device?.firmwareVersion ?? null,
      });
      setLogNotes('');
    } finally {
      setSaving(false);
    }
  }

  if (isLoading && !device) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Loading device health…</Text>
      </View>
    );
  }

  if (!device) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Device not found</Text>
        <Text style={styles.line}>ID: {deviceId}</Text>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Device health</Text>
      <Text style={styles.line}>Device: {device.deviceId}</Text>
      <Text style={styles.line}>Firmware: {device.firmwareVersion}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Lifetime stats</Text>
        <Text style={styles.line}>Motor hours: {device.motorHours.toFixed(1)}</Text>
        <Text style={styles.line}>Total falls caught: {device.totalFallsCaught}</Text>
        <Text style={styles.line}>Cycle count: {device.cycleCount}</Text>
        {daysUntilInspection !== null && (
          <Text style={styles.line}>
            Days until next inspection: {daysUntilInspection}
          </Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Last maintenance</Text>
        {lastLog ? (
          <>
            <Text style={styles.line}>
              Action: {lastLog.action} by {lastLog.performedByName}
            </Text>
            <Text style={styles.line}>
              When: {lastLog.timestamp.toLocaleString()}
            </Text>
            {lastLog.notes ? (
              <Text style={styles.line}>Notes: {lastLog.notes}</Text>
            ) : null}
          </>
        ) : (
          <Text style={styles.line}>No maintenance logs recorded yet.</Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Log manual inspection</Text>
        <Text style={styles.line}>
          Use this after a visual/mechanical inspection or test fall sequence.
        </Text>
        <TextInput
          style={styles.input}
          multiline
          placeholder="Inspection notes (what you checked, issues found, etc.)"
          value={logNotes}
          onChangeText={setLogNotes}
        />
        <TouchableOpacity
          style={[styles.button, saving && styles.buttonDisabled]}
          onPress={handleLogInspection}
          disabled={saving}
        >
          <Text style={styles.buttonText}>
            {saving ? 'Saving…' : 'Log manual inspection'}
          </Text>
        </TouchableOpacity>
      </View>

      {logs.length > 1 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>History</Text>
          {logs.slice(1).map((log) => (
            <View key={log.id} style={styles.logRow}>
              <Text style={styles.logMain}>
                {log.action} by {log.performedByName}
              </Text>
              <Text style={styles.logSub}>
                {log.timestamp.toLocaleString()}
                {log.notes ? ` — ${log.notes}` : ''}
              </Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
  },
  title: { fontSize: 22, marginBottom: 8 },
  line: { color: '#444', marginBottom: 4 },
  card: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 16,
    marginTop: 16,
    backgroundColor: '#fff',
  },
  cardTitle: { fontSize: 18, marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    minHeight: 60,
    marginTop: 8,
    marginBottom: 12,
  },
  button: {
    backgroundColor: '#1a1a2e',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  logRow: {
    marginBottom: 8,
  },
  logMain: {
    fontSize: 14,
    fontWeight: '500',
  },
  logSub: {
    fontSize: 12,
    color: '#6b7280',
  },
});

