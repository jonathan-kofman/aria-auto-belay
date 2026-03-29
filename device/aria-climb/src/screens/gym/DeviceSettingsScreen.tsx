import React, { useState } from 'react';
import { View, Text, Switch, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

export function DeviceSettingsScreen() {
  const { t } = useTranslation();
  const [safeMode, setSafeMode] = useState(true);
  const [autoPauseOnZone, setAutoPauseOnZone] = useState(true);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('gym.settings')}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Global safety</Text>

        <View style={styles.row}>
          <View style={styles.info}>
            <Text style={styles.label}>Safe mode</Text>
            <Text style={styles.value}>
              {safeMode ? 'ARIA will err on the side of pausing' : 'Normal behavior'}
            </Text>
          </View>
          <Switch value={safeMode} onValueChange={setSafeMode} />
        </View>

        <View style={styles.row}>
          <View style={styles.info}>
            <Text style={styles.label}>Auto-pause on zone intrusion</Text>
            <Text style={styles.value}>
              {autoPauseOnZone
                ? 'Pause motor when fall zone is occupied'
                : 'Show alert only; do not auto-pause'}
            </Text>
          </View>
          <Switch value={autoPauseOnZone} onValueChange={setAutoPauseOnZone} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 16 },
  card: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 16,
    backgroundColor: '#fff',
  },
  cardTitle: { fontSize: 18, marginBottom: 12 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  info: { flex: 1, paddingRight: 12 },
  label: { fontSize: 12, color: '#888' },
  value: { fontSize: 14, color: '#222', marginTop: 2 },
});
