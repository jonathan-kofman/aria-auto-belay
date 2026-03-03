import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, LayoutAnimation, Platform, UIManager } from 'react-native';
import { useAuthStore } from '../../store/authStore';
import { useARIADevice } from '../../hooks/useARIADevice';
import type { ARIAState } from '../../types/aria';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type Props = {
  deviceId: string;
};

type StateColor = {
  bg: string;
  border: string;
  text: string;
};

const STATE_COLORS: Record<ARIAState, StateColor> = {
  IDLE: { bg: '#e5e7eb', border: '#9ca3af', text: '#111827' },
  CLIMBING: { bg: '#dcfce7', border: '#22c55e', text: '#14532d' },
  CLIPPING: { bg: '#e0f2fe', border: '#0ea5e9', text: '#0f172a' },
  TAKE: { bg: '#fef9c3', border: '#facc15', text: '#78350f' },
  REST: { bg: '#f5f3ff', border: '#a855f7', text: '#4c1d95' },
  LOWER: { bg: '#e0f2fe', border: '#38bdf8', text: '#0f172a' },
  WATCH_ME: { bg: '#ffedd5', border: '#f97316', text: '#7c2d12' },
  UP: { bg: '#e0e7ff', border: '#6366f1', text: '#111827' },
  FAULT: { bg: '#fee2e2', border: '#ef4444', text: '#7f1d1d' },
  LOCKOUT: { bg: '#fee2e2', border: '#b91c1c', text: '#7f1d1d' },
  MAINTENANCE: { bg: '#fef3c7', border: '#f59e0b', text: '#78350f' },
};

const ORDERED_STATES: ARIAState[] = [
  'IDLE',
  'CLIMBING',
  'CLIPPING',
  'TAKE',
  'REST',
  'LOWER',
  'WATCH_ME',
  'UP',
  'FAULT',
  'LOCKOUT',
  'MAINTENANCE',
];

type HistoryEntry = { state: ARIAState; at: number };

export function StateMachineViz({ deviceId }: Props) {
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';
  const { device } = useARIADevice(gymId, deviceId);

  const liveState = (device?.state as ARIAState) || 'IDLE';
  const [current, setCurrent] = useState<ARIAState>(liveState);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    if (!liveState || liveState === current) return;
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setCurrent(liveState);
    setHistory((prev) => {
      const next: HistoryEntry[] = [{ state: liveState, at: Date.now() }, ...prev];
      return next.slice(0, 5);
    });
  }, [liveState, current]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>State machine</Text>
      <View style={styles.row}>
        {ORDERED_STATES.map((s) => {
          const colors = STATE_COLORS[s];
          const active = s === current;
          return (
            <View
              key={s}
              style={[
                styles.stateChip,
                { backgroundColor: colors.bg, borderColor: colors.border },
                active && styles.stateChipActive,
              ]}
            >
              <View
                style={[
                  styles.dot,
                  { backgroundColor: colors.border },
                  active && styles.dotActive,
                ]}
              />
              <Text style={[styles.stateLabel, { color: colors.text }]}>{s}</Text>
            </View>
          );
        })}
      </View>

      <Text style={styles.subtitle}>Recent transitions</Text>
      {history.length === 0 ? (
        <Text style={styles.empty}>Waiting for first state change…</Text>
      ) : (
        <View style={styles.historyRow}>
          {history.map((h, idx) => {
            const colors = STATE_COLORS[h.state];
            const ageSec = (Date.now() - h.at) / 1000;
            return (
              <View
                key={`${h.state}-${h.at}-${idx}`}
                style={[styles.historyChip, { borderColor: colors.border }]}
              >
                <Text style={[styles.historyText, { color: colors.text }]}>{h.state}</Text>
                <Text style={styles.historyTime}>{ageSec.toFixed(1)}s ago</Text>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 8 },
  title: { fontSize: 16, fontWeight: '600', marginBottom: 8 },
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  } as any,
  stateChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    marginBottom: 4,
  },
  stateChipActive: {
    transform: [{ scale: 1.05 }],
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 4,
    opacity: 0.7,
  },
  dotActive: {
    opacity: 1,
  },
  stateLabel: {
    fontSize: 11,
    fontWeight: '500',
  },
  subtitle: { fontSize: 14, marginTop: 8, marginBottom: 4 },
  empty: { fontSize: 12, color: '#6b7280' },
  historyRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  } as any,
  historyChip: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginBottom: 4,
  },
  historyText: { fontSize: 11, fontWeight: '500' },
  historyTime: { fontSize: 10, color: '#6b7280' },
});

