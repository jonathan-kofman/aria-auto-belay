import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';

const MOCK_STATUS = {
  wall: 'Lead Wall 3 – 5.11b',
  nextSlot: 'Tonight 7:30–8:00 PM',
  deviceStatus: 'Ready',
};

const LAST_SESSION = {
  routeName: 'Lead Wall 2 – 5.11a',
  date: 'Feb 28, 2026',
  maxHeight: 14.2,
  clips: 18,
  falls: 1,
};

export function HomeScreen() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const navigation = useNavigation<any>();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('climber.home')}</Text>
      <Text style={styles.subtitle}>
        {user?.displayName ? `Hi, ${user.displayName}` : 'Hi climber'}
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Wall status</Text>
        <Text style={styles.cardLine}>{MOCK_STATUS.wall}</Text>
        <Text style={styles.cardLine}>ARIA: {MOCK_STATUS.deviceStatus}</Text>
        <Text style={styles.cardLine}>Next slot: {MOCK_STATUS.nextSlot}</Text>
        <TouchableOpacity
          style={styles.primaryButton}
          onPress={() => (navigation as any).navigate('PairDevice')}
        >
          <Text style={styles.primaryButtonText}>Pair with ARIA &amp; start climbing</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => navigation.navigate('Sessions')}
        >
          <Text style={styles.secondaryButtonText}>{t('climber.book_wall')}</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{t('climber.my_sessions')}</Text>
        <Text style={styles.cardLine}>{LAST_SESSION.routeName}</Text>
        <Text style={styles.cardLine}>{LAST_SESSION.date}</Text>
        <Text style={styles.cardLine}>
          Max height: {LAST_SESSION.maxHeight.toFixed(1)} m · Clips: {LAST_SESSION.clips} · Falls:{' '}
          {LAST_SESSION.falls}
        </Text>
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => navigation.navigate('Sessions')}
        >
          <Text style={styles.secondaryButtonText}>View all sessions</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{t('climber.personal_bests')}</Text>
        <Text style={styles.cardLine}>
          {t('climber.max_height')}: 15.3 m
        </Text>
        <Text style={styles.cardLine}>
          {t('climber.total_clips')}: 420
        </Text>
        <Text style={styles.cardLine}>
          {t('climber.total_falls')}: 12
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 4 },
  subtitle: { marginBottom: 16, color: '#666' },
  card: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 16,
    marginBottom: 16,
    backgroundColor: '#fff',
  },
  cardTitle: { fontSize: 18, marginBottom: 8 },
  cardLine: { color: '#444', marginBottom: 4 },
  primaryButton: {
    marginTop: 12,
    backgroundColor: '#1a1a2e',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#fff', fontSize: 16 },
  secondaryButton: {
    marginTop: 8,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#1a1a2e',
    alignItems: 'center',
  },
  secondaryButtonText: { color: '#1a1a2e', fontSize: 14 },
});
