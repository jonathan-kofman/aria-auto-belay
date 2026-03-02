import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import type { ClimberStackParamList } from '../../types/navigation';

const SESSIONS = [
  {
    id: 's1',
    date: 'Feb 28, 2026',
    wall: 'Lead Wall 2 – 5.11a',
    durationMinutes: 42,
    maxHeight: 14.2,
    clips: 18,
    falls: 1,
    notes: 'Felt good, small slip at the crux.',
  },
  {
    id: 's2',
    date: 'Feb 24, 2026',
    wall: 'Lead Wall 1 – 5.10d',
    durationMinutes: 35,
    maxHeight: 13.0,
    clips: 15,
    falls: 0,
    notes: 'Clean send, warmed up on this route.',
  },
];

export function SessionDetailScreen() {
  const route = useRoute<RouteProp<ClimberStackParamList, 'SessionDetail'>>();
  const { sessionId } = route.params;

  const session = SESSIONS.find((s) => s.id === sessionId);

  if (!session) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Session not found</Text>
        <Text style={styles.line}>ID: {sessionId}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{session.wall}</Text>
      <Text style={styles.line}>{session.date}</Text>
      <Text style={styles.line}>Duration: {session.durationMinutes} min</Text>
      <Text style={styles.line}>Max height: {session.maxHeight.toFixed(1)} m</Text>
      <Text style={styles.line}>Clips: {session.clips}</Text>
      <Text style={styles.line}>Falls: {session.falls}</Text>
      <Text style={[styles.line, styles.notes]}>{session.notes}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 8 },
  line: { color: '#444', marginBottom: 4 },
  notes: { marginTop: 12 },
});
