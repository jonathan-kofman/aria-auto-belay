import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';
import { subscribeToSessions } from '../../services/firebase/sessions';
import type { Session } from '../../types/aria';

const SESSIONS = [
  {
    id: 'g1',
    deviceId: 'ARIA-02',
    climber: 'Demo climber',
    date: 'Feb 28, 2026',
    wall: 'Lead Wall 2',
    route: '5.11b – Techy face',
    falls: 1,
  },
  {
    id: 'g2',
    deviceId: 'ARIA-01',
    climber: 'Alex',
    date: 'Feb 28, 2026',
    wall: 'Lead Wall 1',
    route: '5.10d – Red line',
    falls: 0,
  },
];

export function SessionHistoryScreen() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!gymId) return;
    const unsub = subscribeToSessions(
      gymId,
      (list) => {
        setSessions(list);
        setLoading(false);
      },
      () => {
        setLoading(false);
      }
    );

    return unsub;
  }, [gymId]);

  const rows =
    sessions.length > 0
      ? sessions.map((s) => ({
          id: s.sessionId,
          deviceId: s.deviceId,
          climber: s.climberDisplayName,
          date: s.startTime.toLocaleDateString(),
          wall: s.wallId,
          route: s.routeName ?? 'Unknown route',
          falls: s.fallCount,
        }))
      : SESSIONS;

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('gym.sessions')}</Text>
      {loading && !sessions.length ? (
        <Text>Loading sessions…</Text>
      ) : (
        <FlatList
          data={rows}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <Text style={styles.device}>{item.deviceId}</Text>
              <View style={styles.info}>
                <Text style={styles.route}>{item.route}</Text>
                <Text style={styles.line}>
                  {item.wall} · {item.date}
                </Text>
                <Text style={styles.line}>
                  Climber: {item.climber} · Falls: {item.falls}
                </Text>
              </View>
            </View>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 12 },
  row: {
    flexDirection: 'row',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  device: { width: 80, fontWeight: '600' },
  info: { flex: 1 },
  route: { fontSize: 14 },
  line: { color: '#444', fontSize: 12, marginTop: 2 },
});
