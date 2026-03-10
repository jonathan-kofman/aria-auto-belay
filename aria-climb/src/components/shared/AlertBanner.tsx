import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useSafetyTestStore } from '../../store/safetyTestStore';

/**
 * Shows when zone intrusion is active (real from device or mock from Safety / Camera test).
 */
export function AlertBanner() {
  const { mockZoneIntrusionActive, setMockZoneIntrusion } = useSafetyTestStore();

  if (!mockZoneIntrusionActive) return null;

  return (
    <View style={styles.banner}>
      <Text style={styles.text}>Fall zone occupied (mock) — motor would pause in production</Text>
      <TouchableOpacity onPress={() => setMockZoneIntrusion(false)} style={styles.button}>
        <Text style={styles.buttonText}>Clear</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#c0392b',
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  text: { color: '#fff', fontSize: 14, flex: 1 },
  button: { paddingVertical: 4, paddingHorizontal: 12 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 14 },
});
