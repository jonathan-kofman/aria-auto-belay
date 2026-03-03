import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  Modal,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';
import { subscribeToIncidents, resolveIncident } from '../../services/firebase/incidents';
import type { Incident } from '../../types/aria';

type Row = {
  id: string;
  time: string;
  deviceId: string;
  type: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  resolved: boolean;
  resolvedBy?: string | null;
};

const ALERTS: Row[] = [
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
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all');
  const [resolveModalVisible, setResolveModalVisible] = useState(false);
  const [resolveNotes, setResolveNotes] = useState('');
  const [resolving, setResolving] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<Row | null>(null);

  useEffect(() => {
    if (!gymId) return;
    const unsub = subscribeToIncidents(
      gymId,
      (list) => {
        setIncidents(list);
        setLoading(false);
      },
      () => {
        setLoading(false);
      }
    );
    return unsub;
  }, [gymId]);

  const rows: Row[] = (incidents.length
    ? incidents.map((inc) => ({
        id: inc.incidentId,
        time: inc.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        deviceId: inc.deviceId,
        type: inc.type,
        message: inc.description,
        severity: inc.severity.toLowerCase() as 'low' | 'medium' | 'high' | 'critical',
        resolved: inc.resolved,
        resolvedBy: inc.resolvedBy,
      }))
    : ALERTS.map((a) => ({ ...a, resolved: false }))).map((a) => a);

  const filteredAlerts = useMemo(() => {
    if (severityFilter === 'all') return rows;
    return rows.filter((a) => a.severity === severityFilter);
  }, [rows, severityFilter]);

  function openResolveModal(row: Row) {
    setSelectedIncident(row);
    setResolveNotes('');
    setResolveModalVisible(true);
  }

  async function handleResolve() {
    if (!selectedIncident || !user) return;
    setResolving(true);
    try {
      await resolveIncident(gymId, selectedIncident.id, user.displayName || user.uid, resolveNotes);
      setResolveModalVisible(false);
      setSelectedIncident(null);
      setResolveNotes('');
    } catch (e) {
      // optional: surface error later
      console.error('Failed to resolve incident', e);
    } finally {
      setResolving(false);
    }
  }

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
      {loading && !incidents.length ? (
        <Text>Loading alerts…</Text>
      ) : (
        <FlatList
          data={filteredAlerts}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <View style={styles.timeCol}>
                <Text style={styles.time}>{item.time}</Text>
                <Text
                  style={[
                    styles.badge,
                    styles[
                      `badge_${item.severity === 'critical' ? 'high' : item.severity}` as const
                    ],
                  ]}
                >
                  {item.severity.toUpperCase()}
                </Text>
              </View>
              <View style={styles.info}>
                <Text style={styles.device}>{item.deviceId}</Text>
                <Text style={styles.message}>{item.message}</Text>
                <Text style={styles.type}>{item.type}</Text>
                {item.resolved && (
                  <Text style={styles.resolved}>
                    ✅ Resolved{item.resolvedBy ? ` by ${item.resolvedBy}` : ''}
                  </Text>
                )}
                {!item.resolved &&
                  (item.severity === 'high' || item.severity === 'critical') &&
                  !!user && (
                    <TouchableOpacity
                      style={styles.resolveButton}
                      onPress={() => openResolveModal(item)}
                    >
                      <Text style={styles.resolveText}>Resolve</Text>
                    </TouchableOpacity>
                  )}
              </View>
            </View>
          )}
        />
      )}

      <Modal visible={resolveModalVisible} transparent animationType="fade">
        <View style={styles.modalBackdrop}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Resolve incident</Text>
            {selectedIncident && (
              <Text style={styles.modalSubtitle}>
                {selectedIncident.deviceId} · {selectedIncident.type}
              </Text>
            )}
            <TextInput
              style={styles.input}
              placeholder="Resolution notes (optional but recommended)"
              value={resolveNotes}
              onChangeText={setResolveNotes}
              multiline
            />
            {resolving && <ActivityIndicator style={{ marginTop: 8 }} />}
            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalPrimary]}
                onPress={handleResolve}
                disabled={resolving}
              >
                <Text style={styles.modalPrimaryText}>
                  {resolving ? 'Resolving…' : 'Resolve incident'}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalButton, styles.modalCancel]}
                onPress={() => setResolveModalVisible(false)}
                disabled={resolving}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  resolved: { fontSize: 11, color: '#16a34a', marginTop: 4 },
  resolveButton: {
    marginTop: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#1a1a2e',
    alignSelf: 'flex-start',
  },
  resolveText: { fontSize: 11, color: '#fff' },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modal: {
    width: '90%',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
  },
  modalTitle: { fontSize: 18, marginBottom: 4 },
  modalSubtitle: { fontSize: 13, color: '#666', marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 10,
    minHeight: 80,
    textAlignVertical: 'top',
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  modalButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  modalPrimary: { backgroundColor: '#1a1a2e' },
  modalPrimaryText: { color: '#fff', fontSize: 14 },
  modalCancel: { backgroundColor: '#e5e7eb' },
  modalCancelText: { color: '#374151', fontSize: 14 },
});
