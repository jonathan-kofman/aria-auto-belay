/**
 * LiveSessionScreen — real-time ARIA device monitoring during a climb.
 *
 * Displays:
 *   - Current state badge (IDLE / ARMED / CLIMBING / FALL_ARREST / FAULT)
 *   - Live tension bar (0–600 N)
 *   - Rope speed indicator
 *   - Battery level
 *   - Disconnect button
 *
 * Receives deviceId from navigation params (set by GymOnboardingScreen).
 */

import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  ScrollView,
} from 'react-native';
import { useRoute, useNavigation } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import type { DrawerNavigationProp } from '@react-navigation/drawer';
import type { ClimberDrawerParamList } from '../../types/navigation';
import { useARIADevice } from '../../hooks/useARIADevice';
import type { ARIAState } from '../../types/aria';
import { TENSION_BASELINE_N, TENSION_FALL_THRESHOLD_N } from '../../types/aria';

type LiveSessionRouteProp = RouteProp<ClimberDrawerParamList, 'LiveSession'>;
type Nav = DrawerNavigationProp<ClimberDrawerParamList>;

// ─── State colours ────────────────────────────────────────────────────────────
const STATE_COLOR: Record<ARIAState, string> = {
  IDLE: '#6b7280',
  ARMED: '#2563eb',
  CLIMBING: '#16a34a',
  FALL_ARREST: '#dc2626',
  FAULT: '#b91c1c',
  UNKNOWN: '#9ca3af',
};

const STATE_LABEL: Record<ARIAState, string> = {
  IDLE: 'Idle',
  ARMED: 'Armed',
  CLIMBING: 'Climbing',
  FALL_ARREST: 'Fall arrest',
  FAULT: 'FAULT',
  UNKNOWN: '—',
};

const MAX_TENSION_N = 600;

// ─── Sub-components ───────────────────────────────────────────────────────────

function StateBadge({ state }: { state: ARIAState }) {
  const pulse = useRef(new Animated.Value(1)).current;
  const isCritical = state === 'FALL_ARREST' || state === 'FAULT';

  useEffect(() => {
    if (isCritical) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulse, { toValue: 1.08, duration: 300, useNativeDriver: true }),
          Animated.timing(pulse, { toValue: 1, duration: 300, useNativeDriver: true }),
        ])
      ).start();
    } else {
      pulse.setValue(1);
    }
    return () => pulse.stopAnimation();
  }, [isCritical, pulse]);

  return (
    <Animated.View
      style={[
        styles.stateBadge,
        { backgroundColor: STATE_COLOR[state], transform: [{ scale: pulse }] },
      ]}
    >
      <Text style={styles.stateText}>{STATE_LABEL[state]}</Text>
    </Animated.View>
  );
}

function TensionBar({ tension_N }: { tension_N: number }) {
  const pct = Math.min(tension_N / MAX_TENSION_N, 1);
  const barColor =
    tension_N >= TENSION_FALL_THRESHOLD_N
      ? '#dc2626'
      : tension_N >= TENSION_BASELINE_N * 3
      ? '#f59e0b'
      : '#16a34a';

  return (
    <View style={styles.tensionWrapper}>
      <View style={styles.tensionLabelRow}>
        <Text style={styles.tensionLabel}>Tension</Text>
        <Text style={[styles.tensionValue, { color: barColor }]}>
          {tension_N.toFixed(0)} N
        </Text>
      </View>
      <View style={styles.barBg}>
        <View style={[styles.barFill, { width: `${pct * 100}%`, backgroundColor: barColor }]} />
      </View>
      <View style={styles.barMarkers}>
        <Text style={styles.markerText}>0</Text>
        <Text style={styles.markerText}>{TENSION_BASELINE_N} N</Text>
        <Text style={styles.markerText}>{TENSION_FALL_THRESHOLD_N} N</Text>
        <Text style={styles.markerText}>{MAX_TENSION_N} N</Text>
      </View>
    </View>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricRow}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export function LiveSessionScreen() {
  const route = useRoute<LiveSessionRouteProp>();
  const navigation = useNavigation<Nav>();
  const { deviceId } = route.params;

  const { telemetry, connected, connecting, connectionError, connect, disconnect } =
    useARIADevice(deviceId);

  // Auto-connect on mount
  useEffect(() => {
    if (!connected && !connecting) {
      connect();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleDisconnect() {
    await disconnect();
    navigation.navigate('Home');
  }

  const state: ARIAState = telemetry?.state ?? 'UNKNOWN';

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Live Session</Text>
      <Text style={styles.deviceId}>{deviceId}</Text>

      {connectionError && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{connectionError}</Text>
          <TouchableOpacity onPress={connect}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {!connected && !connectionError && (
        <Text style={styles.connectingText}>
          {connecting ? 'Connecting…' : 'Not connected'}
        </Text>
      )}

      {/* State badge */}
      <StateBadge state={state} />

      {/* Tension bar */}
      <TensionBar tension_N={telemetry?.tension_N ?? 0} />

      {/* Metrics */}
      <View style={styles.metricsCard}>
        <MetricRow
          label="Rope speed"
          value={
            telemetry
              ? `${telemetry.rope_speed_ms >= 0 ? '+' : ''}${telemetry.rope_speed_ms.toFixed(2)} m/s`
              : '—'
          }
        />
        <MetricRow
          label="Motor current"
          value={telemetry ? `${telemetry.motor_current_A.toFixed(1)} A` : '—'}
        />
        <MetricRow
          label="Battery"
          value={telemetry ? `${telemetry.battery_V.toFixed(1)} V` : '—'}
        />
        <MetricRow
          label="Last update"
          value={
            telemetry
              ? new Date(telemetry.ts).toLocaleTimeString()
              : '—'
          }
        />
      </View>

      <TouchableOpacity style={styles.disconnectButton} onPress={handleDisconnect}>
        <Text style={styles.disconnectText}>End session</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: 24, alignItems: 'center' },
  title: { fontSize: 24, fontWeight: '700', marginBottom: 4 },
  deviceId: { color: '#6b7280', fontSize: 13, marginBottom: 24 },
  connectingText: { color: '#6b7280', marginBottom: 24 },
  errorBox: {
    backgroundColor: '#fee2e2',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    width: '100%',
    alignItems: 'center',
  },
  errorText: { color: '#dc2626', fontSize: 14 },
  retryText: { color: '#1a1a2e', fontSize: 14, marginTop: 8, fontWeight: '600' },

  // State badge
  stateBadge: {
    paddingVertical: 12,
    paddingHorizontal: 40,
    borderRadius: 100,
    marginBottom: 32,
  },
  stateText: { color: '#fff', fontSize: 20, fontWeight: '700', letterSpacing: 1 },

  // Tension bar
  tensionWrapper: { width: '100%', marginBottom: 24 },
  tensionLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  tensionLabel: { fontSize: 16, fontWeight: '600' },
  tensionValue: { fontSize: 16, fontWeight: '700' },
  barBg: {
    height: 20,
    backgroundColor: '#e5e7eb',
    borderRadius: 10,
    overflow: 'hidden',
  },
  barFill: { height: '100%', borderRadius: 10 },
  barMarkers: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  markerText: { fontSize: 10, color: '#9ca3af' },

  // Metrics
  metricsCard: {
    width: '100%',
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: '#e5e7eb',
  },
  metricLabel: { color: '#6b7280', fontSize: 14 },
  metricValue: { fontSize: 14, fontWeight: '600', color: '#111827' },

  disconnectButton: {
    borderWidth: 1,
    borderColor: '#dc2626',
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 32,
  },
  disconnectText: { color: '#dc2626', fontSize: 16, fontWeight: '600' },
});
