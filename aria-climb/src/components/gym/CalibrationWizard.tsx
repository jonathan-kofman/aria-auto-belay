import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity } from 'react-native';
import firestore from '@react-native-firebase/firestore';
import { useAuthStore } from '../../store/authStore';
import { useARIADevice } from '../../hooks/useARIADevice';
import { issueCommand } from '../../services/firebase/ariaDevice';
import { COLLECTIONS } from '../../types/aria';

type Props = {
  deviceId: string;
};

type StepId = 1 | 2 | 3 | 4 | 5;

export function CalibrationWizard({ deviceId }: Props) {
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';
  const { device } = useARIADevice(gymId, deviceId);

  const [step, setStep] = useState<StepId>(1);
  const [knownWeight, setKnownWeight] = useState('80'); // kg
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const tension = device?.tension ?? 0;

  async function handleSave() {
    if (!user || !gymId) return;
    setSaving(true);
    try {
      const ref = firestore().doc(COLLECTIONS.device(gymId, deviceId));
      await ref.set(
        {
          lastCalibrationAt: firestore.Timestamp.now(),
          lastCalibrationBy: user.displayName || user.uid,
          lastCalibrationNotes: notes || null,
        },
        { merge: true }
      );
      await issueCommand({
        deviceId,
        gymId,
        command: 'CALIBRATE_ENCODER',
        params: {},
        issuedBy: user.uid,
        issuedByName: user.displayName,
        issuedAt: firestore.Timestamp.now() as any,
      });
      setStep(5);
    } catch (e) {
      console.error('Calibration save failed', e);
    } finally {
      setSaving(false);
    }
  }

  function next() {
    setStep((s) => (s < 5 ? ((s + 1) as StepId) : s));
  }

  function back() {
    setStep((s) => (s > 1 ? ((s - 1) as StepId) : s));
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Calibration wizard</Text>
      <Text style={styles.subtitle}>Device: {deviceId}</Text>

      {step === 1 && (
        <View style={styles.step}>
          <Text style={styles.stepTitle}>1. Hang known weight on the rope</Text>
          <Text style={styles.text}>
            Attach a known calibration weight to the harness (or rope) and let the system settle.
          </Text>
          <TextInput
            style={styles.input}
            keyboardType="numeric"
            placeholder="Known weight (kg)"
            value={knownWeight}
            onChangeText={setKnownWeight}
          />
          <Text style={styles.text}>Live tension: {tension.toFixed(1)} N</Text>
        </View>
      )}

      {step === 2 && (
        <View style={styles.step}>
          <Text style={styles.stepTitle}>2. Verify load cell reading</Text>
          <Text style={styles.text}>
            Compare the displayed tension to the expected weight (mass × 9.81). Adjust calibration
            factors in firmware if the error is large.
          </Text>
          <Text style={styles.text}>Known weight: {knownWeight} kg</Text>
          <Text style={styles.text}>
            Expected: {(parseFloat(knownWeight || '0') * 9.81).toFixed(1)} N
          </Text>
          <Text style={styles.text}>Measured: {tension.toFixed(1)} N</Text>
        </View>
      )}

      {step === 3 && (
        <View style={styles.step}>
          <Text style={styles.stepTitle}>3. Encoder zero position</Text>
          <Text style={styles.text}>
            Move the rope to the mechanical zero (fully retracted reference point), then ensure the
            encoder count in the device document is close to zero.
          </Text>
          <Text style={styles.text}>
            Current ropeOut: {device ? device.ropeOut.toFixed(2) : '—'} m
          </Text>
        </View>
      )}

      {step === 4 && (
        <View style={styles.step}>
          <Text style={styles.stepTitle}>4. Motor direction test</Text>
          <Text style={styles.text}>
            From the app or test harness, command a small UP and DOWN movement and verify that rope
            motion matches the intended direction.
          </Text>
          <Text style={styles.text}>
            Watch the rope and ensure there is no inversion between commanded and actual direction.
          </Text>
        </View>
      )}

      {step === 5 && (
        <View style={styles.step}>
          <Text style={styles.stepTitle}>5. Save calibration</Text>
          <Text style={styles.text}>
            These notes will be stored with the device in Firebase and the STM32 will be asked to
            re-calibrate its encoder.
          </Text>
          <TextInput
            style={[styles.input, { height: 80 }]}
            placeholder="Calibration notes (e.g. weight used, observations)"
            multiline
            value={notes}
            onChangeText={setNotes}
          />
        </View>
      )}

      <View style={styles.buttonsRow}>
        <TouchableOpacity
          style={[styles.button, styles.secondaryButton]}
          onPress={back}
          disabled={step === 1}
        >
          <Text style={styles.buttonText}>Back</Text>
        </TouchableOpacity>
        {step < 5 ? (
          <TouchableOpacity style={styles.button} onPress={next}>
            <Text style={styles.buttonText}>Next</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.button, saving && styles.buttonDisabled]}
            onPress={handleSave}
            disabled={saving}
          >
            <Text style={styles.buttonText}>{saving ? 'Saving…' : 'Save & calibrate'}</Text>
          </TouchableOpacity>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 8 },
  title: { fontSize: 16, fontWeight: '600' },
  subtitle: { fontSize: 12, color: '#6b7280', marginBottom: 8 },
  step: { marginTop: 8 },
  stepTitle: { fontSize: 14, fontWeight: '600', marginBottom: 4 },
  text: { fontSize: 12, color: '#374151', marginBottom: 4 },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 8,
  },
  buttonsRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 12,
  },
  button: {
    backgroundColor: '#1a1a2e',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginLeft: 8,
  },
  secondaryButton: {
    backgroundColor: '#e5e7eb',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: { fontSize: 12, color: '#ffffff' },
});

