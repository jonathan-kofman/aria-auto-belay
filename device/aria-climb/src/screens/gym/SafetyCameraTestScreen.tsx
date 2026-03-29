import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Linking,
  Platform,
} from 'react-native';
import { useSafetyTestStore } from '../../store/safetyTestStore';

// Optional: expo-camera for live preview. If not installed, we still support mock zone intrusion.
let CameraView: React.ComponentType<any> | null = null;
let useCameraPermissions: () => [{ granted: boolean | null; canAskAgain: boolean }, () => Promise<{ granted: boolean }>] = () => [{ granted: null, canAskAgain: false }, async () => ({ granted: false })];
try {
  const expoCamera = require('expo-camera');
  CameraView = expoCamera.CameraView;
  useCameraPermissions = expoCamera.useCameraPermissions;
} catch {
  // expo-camera not installed
}

export function SafetyCameraTestScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [cameraReady, setCameraReady] = useState(false);
  const { mockZoneIntrusionActive, setMockZoneIntrusion } = useSafetyTestStore();

  const hasCameraModule = CameraView != null;
  const permissionGranted = permission?.granted === true;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Safety & Camera test</Text>
      <Text style={styles.subtitle}>
        Verify camera for zone monitoring and run the same alert flow as real hardware (mock).
      </Text>

      {/* 1. Camera permission */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>1. Camera permission</Text>
        {!hasCameraModule ? (
          <Text style={styles.hint}>
            Install expo-camera for live preview: run in project folder:{'\n'}
            <Text style={styles.code}>npx expo install expo-camera</Text>
            {'\n'}Then rebuild: <Text style={styles.code}>npx expo run:android</Text> (or run:ios)
          </Text>
        ) : (
          <>
            <Text style={styles.status}>
              Status: {permissionGranted ? 'Granted' : permission?.canAskAgain ? 'Not granted' : 'Denied (enable in device settings)'}
            </Text>
            {!permissionGranted && permission?.canAskAgain === true && (
              <TouchableOpacity style={styles.button} onPress={requestPermission}>
                <Text style={styles.buttonText}>Request camera permission</Text>
              </TouchableOpacity>
            )}
            {!permissionGranted && permission?.canAskAgain === false && (
              <TouchableOpacity
                style={styles.button}
                onPress={() => Linking.openSettings()}
              >
                <Text style={styles.buttonText}>Open settings</Text>
              </TouchableOpacity>
            )}
          </>
        )}
      </View>

      {/* 2. Live preview */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>2. Live preview</Text>
        {hasCameraModule && permissionGranted && CameraView ? (
          <View style={styles.previewContainer}>
            <CameraView
              style={styles.preview}
              facing="back"
              onCameraReady={() => setCameraReady(true)}
            />
            {!cameraReady && (
              <View style={styles.previewOverlay}>
                <Text style={styles.previewOverlayText}>Starting camera…</Text>
              </View>
            )}
          </View>
        ) : (
          <View style={styles.placeholder}>
            <Text style={styles.placeholderText}>
              {!hasCameraModule
                ? 'Install expo-camera and rebuild to see live preview'
                : !permissionGranted
                  ? 'Grant camera permission above to see preview'
                  : 'Camera preview'}
            </Text>
          </View>
        )}
      </View>

      {/* 3. Mock zone intrusion */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>3. Mock zone intrusion</Text>
        <Text style={styles.hint}>
          Simulates the device reporting "fall zone occupied". Use this to verify the alert flow
          (banner, Alert history) without real hardware.
        </Text>
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.button, styles.buttonPrimary]}
            onPress={() => setMockZoneIntrusion(true)}
          >
            <Text style={styles.buttonText}>Simulate zone intrusion</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.button, mockZoneIntrusionActive && styles.buttonDanger]}
            onPress={() => setMockZoneIntrusion(false)}
          >
            <Text style={styles.buttonText}>Clear zone</Text>
          </TouchableOpacity>
        </View>
        {mockZoneIntrusionActive && (
          <Text style={styles.activeHint}>Active — check the alert banner at top and Alert history in the drawer.</Text>
        )}
      </View>

      {/* Checklist */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Verify</Text>
        <Text style={styles.checkItem}>• Camera permission granted (or install expo-camera)</Text>
        <Text style={styles.checkItem}>• Preview visible when permission granted</Text>
        <Text style={styles.checkItem}>• "Simulate zone intrusion" shows alert banner</Text>
        <Text style={styles.checkItem}>• Alert history shows the event when you open it</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, paddingBottom: 40 },
  title: { fontSize: 22, fontWeight: '700', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 24 },
  section: {
    marginBottom: 24,
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#eee',
  },
  sectionTitle: { fontSize: 17, fontWeight: '600', marginBottom: 8 },
  status: { fontSize: 14, color: '#333', marginBottom: 8 },
  hint: { fontSize: 13, color: '#555', marginBottom: 8, lineHeight: 20 },
  code: { fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace', fontSize: 12 },
  button: {
    backgroundColor: '#333',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  buttonPrimary: { backgroundColor: '#0a7ea4' },
  buttonDanger: { backgroundColor: '#c0392b' },
  buttonText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  buttonRow: { flexDirection: 'row', gap: 12, marginTop: 8 },
  previewContainer: { height: 200, borderRadius: 8, overflow: 'hidden', backgroundColor: '#000' },
  preview: { flex: 1, width: '100%', height: '100%' },
  previewOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  previewOverlayText: { color: '#fff', fontSize: 14 },
  placeholder: {
    height: 120,
    borderRadius: 8,
    backgroundColor: '#ddd',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  placeholderText: { fontSize: 13, color: '#666', textAlign: 'center' },
  activeHint: { marginTop: 12, fontSize: 13, color: '#c0392b', fontWeight: '500' },
  checkItem: { fontSize: 14, color: '#333', marginBottom: 4 },
});
