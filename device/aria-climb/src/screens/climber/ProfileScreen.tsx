import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Switch } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';

export function ProfileScreen() {
  const { t } = useTranslation();
  const { user, signOut } = useAuthStore();
  const [metricUnits, setMetricUnits] = useState(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('climber.profile')}</Text>

      {user && (
        <View style={styles.card}>
          <Text style={styles.label}>Name</Text>
          <Text style={styles.value}>{user.displayName || user.email}</Text>

          {user.role && (
            <>
              <Text style={styles.label}>Role</Text>
              <Text style={styles.value}>{user.role === 'climber' ? 'Climber' : 'Gym manager'}</Text>
            </>
          )}

          {user.homeGymId && (
            <>
              <Text style={styles.label}>Home gym</Text>
              <Text style={styles.value}>{user.homeGymId}</Text>
            </>
          )}
        </View>
      )}

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Preferences</Text>

        <View style={styles.row}>
          <View>
            <Text style={styles.label}>Units</Text>
            <Text style={styles.value}>{metricUnits ? 'Metric (m, kg)' : 'Imperial (ft, lb)'}</Text>
          </View>
          <Switch value={metricUnits} onValueChange={setMetricUnits} />
        </View>

        <View style={styles.row}>
          <View>
            <Text style={styles.label}>Notifications</Text>
            <Text style={styles.value}>
              {notificationsEnabled ? 'Session + safety alerts' : 'Off for now'}
            </Text>
          </View>
          <Switch value={notificationsEnabled} onValueChange={setNotificationsEnabled} />
        </View>
      </View>

      <TouchableOpacity onPress={() => signOut()} style={styles.logoutButton}>
        <Text style={styles.logoutText}>{t('auth.logout')}</Text>
      </TouchableOpacity>
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
    marginBottom: 16,
    backgroundColor: '#fff',
  },
  cardTitle: { fontSize: 18, marginBottom: 12 },
  label: { fontSize: 12, color: '#888', marginTop: 8 },
  value: { fontSize: 14, color: '#222', marginTop: 2 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  logoutButton: {
    marginTop: 8,
    padding: 12,
    backgroundColor: '#eee',
    borderRadius: 8,
    alignItems: 'center',
  },
  logoutText: { color: '#333' },
});
