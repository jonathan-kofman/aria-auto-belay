/**
 * GymOnboardingScreen — climber-facing device pairing flow.
 *
 * Flow:
 *   Step 1: Scan QR code on the ARIA unit at the wall
 *   Step 2: App scans BLE for the device encoded in QR, confirms RSSI > threshold
 *   Step 3: Connect + verify device is IDLE/ARMED, show wall label
 *   Step 4: Navigate to LiveSession
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { DrawerNavigationProp } from '@react-navigation/drawer';
import type { ClimberDrawerParamList } from '../../types/navigation';
import { useBleStore } from '../../store/bleStore';
import { startScan, stopScan, connect } from '../../services/ble/bleManager';
import { ARIA_DEVICE_NAME_PREFIX } from '../../services/ble/bleCharacteristics';

type Nav = DrawerNavigationProp<ClimberDrawerParamList>;

type Step = 'qr' | 'scanning' | 'confirm' | 'connecting' | 'done' | 'error';

/** Parse ARIA QR payload. Format: "ARIA:<deviceId>:<wallLabel>" */
function parseQRPayload(raw: string): { deviceId: string; wallLabel: string } | null {
  const parts = raw.trim().split(':');
  if (parts.length < 2 || parts[0] !== 'ARIA') return null;
  return { deviceId: parts[1], wallLabel: parts.slice(2).join(':') || parts[1] };
}

export function GymOnboardingScreen() {
  const navigation = useNavigation<Nav>();
  const [step, setStep] = useState<Step>('qr');
  const [qrResult, setQrResult] = useState<{ deviceId: string; wallLabel: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [manualId, setManualId] = useState('');

  const discoveredDevices = useBleStore((s) => s.discoveredDevices);
  const scanning = useBleStore((s) => s.scanning);
  const scanError = useBleStore((s) => s.scanError);
  const connectionError = useBleStore((s) => s.connectionError);

  const scanTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // When a QR is scanned (or entered manually), start BLE scan
  const onQRScanned = useCallback((raw: string) => {
    const parsed = parseQRPayload(raw);
    if (!parsed) {
      setErrorMsg(`Invalid QR code: "${raw}". Expected format: ARIA:<deviceId>:<wall>`);
      setStep('error');
      return;
    }
    setQrResult(parsed);
    setStep('scanning');
    startScan();
    // Auto-stop after 15 s
    scanTimeoutRef.current = setTimeout(() => {
      stopScan();
      setErrorMsg('Device not found nearby. Make sure you are close to the wall.');
      setStep('error');
    }, 15_000);
  }, []);

  // Watch for the target device appearing in scan results
  useEffect(() => {
    if (step !== 'scanning' || !qrResult) return;
    const target = discoveredDevices.get(qrResult.deviceId);
    if (target) {
      if (scanTimeoutRef.current) {
        clearTimeout(scanTimeoutRef.current);
        scanTimeoutRef.current = null;
      }
      stopScan();
      setStep('confirm');
    }
  }, [discoveredDevices, step, qrResult]);

  // Propagate scan errors
  useEffect(() => {
    if (scanError && step === 'scanning') {
      stopScan();
      setErrorMsg(scanError);
      setStep('error');
    }
  }, [scanError, step]);

  async function handleConnect() {
    if (!qrResult) return;
    setStep('connecting');
    await connect(qrResult.deviceId);
    if (connectionError) {
      setErrorMsg(connectionError);
      setStep('error');
      return;
    }
    setStep('done');
    // Short delay so user sees success state, then navigate
    setTimeout(() => {
      navigation.navigate('LiveSession', { deviceId: qrResult.deviceId });
    }, 800);
  }

  function handleRetry() {
    setStep('qr');
    setQrResult(null);
    setErrorMsg('');
  }

  // ── Render ────────────────────────────────────────────────────────────────

  if (step === 'qr') {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Pair with ARIA</Text>
        <Text style={styles.body}>
          Scan the QR code on the ARIA auto-belay unit at your wall. The QR code is usually on the
          side panel.
        </Text>

        {/* In a real build, replace this View with a Camera/QR scanner component.
            For now, provide a demo button that simulates a scan. */}
        <View style={styles.qrPlaceholder}>
          <Text style={styles.qrPlaceholderText}>[ Camera QR scanner here ]</Text>
          <Text style={styles.qrHint}>Requires react-native-vision-camera + zxing</Text>
        </View>

        <TouchableOpacity
          style={styles.demoButton}
          onPress={() => onQRScanned('ARIA:ARIA-WALL3:Lead Wall 3')}
        >
          <Text style={styles.buttonText}>Simulate QR scan (demo)</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (step === 'scanning') {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#1a1a2e" />
        <Text style={styles.statusText}>Searching for {qrResult?.deviceId}…</Text>
        <Text style={styles.hint}>Stay within 2 m of the wall</Text>
        <TouchableOpacity style={styles.cancelButton} onPress={() => { stopScan(); handleRetry(); }}>
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (step === 'confirm') {
    const device = qrResult ? discoveredDevices.get(qrResult.deviceId) : null;
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Device found</Text>
        <View style={styles.card}>
          <Text style={styles.deviceName}>{qrResult?.wallLabel || qrResult?.deviceId}</Text>
          <Text style={styles.deviceSub}>ID: {device?.id}</Text>
          <Text style={styles.deviceSub}>Signal: {device?.rssi ?? '?'} dBm</Text>
        </View>
        <Text style={styles.body}>
          Connect to this ARIA unit to start your session and receive live tension feedback.
        </Text>
        <TouchableOpacity style={styles.primaryButton} onPress={handleConnect}>
          <Text style={styles.buttonText}>Connect and start session</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.cancelButton} onPress={handleRetry}>
          <Text style={styles.cancelText}>Cancel</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (step === 'connecting') {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#1a1a2e" />
        <Text style={styles.statusText}>Connecting to {qrResult?.deviceId}…</Text>
      </View>
    );
  }

  if (step === 'done') {
    return (
      <View style={styles.container}>
        <Text style={styles.successIcon}>✓</Text>
        <Text style={styles.statusText}>Connected!</Text>
      </View>
    );
  }

  // error
  return (
    <View style={styles.container}>
      <Text style={styles.errorIcon}>✗</Text>
      <Text style={styles.errorText}>{errorMsg || 'Something went wrong.'}</Text>
      <TouchableOpacity style={styles.primaryButton} onPress={handleRetry}>
        <Text style={styles.buttonText}>Try again</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 24, fontWeight: '700', marginBottom: 12, textAlign: 'center' },
  body: { color: '#555', textAlign: 'center', marginBottom: 24, lineHeight: 20 },
  qrPlaceholder: {
    width: 260,
    height: 260,
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#d1d5db',
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
  },
  qrPlaceholderText: { color: '#6b7280', fontSize: 14, textAlign: 'center' },
  qrHint: { color: '#9ca3af', fontSize: 11, marginTop: 6, textAlign: 'center' },
  demoButton: {
    backgroundColor: '#374151',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginBottom: 12,
  },
  primaryButton: {
    backgroundColor: '#1a1a2e',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 8,
    marginBottom: 12,
    width: '100%',
    alignItems: 'center',
  },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  cancelButton: { padding: 12 },
  cancelText: { color: '#6b7280', fontSize: 14 },
  card: {
    width: '100%',
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    padding: 16,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  deviceName: { fontSize: 20, fontWeight: '700', marginBottom: 4 },
  deviceSub: { color: '#6b7280', fontSize: 13 },
  statusText: { fontSize: 18, marginTop: 16, color: '#1a1a2e', textAlign: 'center' },
  hint: { color: '#9ca3af', fontSize: 13, marginTop: 8 },
  successIcon: { fontSize: 64, color: '#16a34a' },
  errorIcon: { fontSize: 64, color: '#dc2626' },
  errorText: { color: '#dc2626', fontSize: 15, textAlign: 'center', marginBottom: 24, marginTop: 8 },
});
