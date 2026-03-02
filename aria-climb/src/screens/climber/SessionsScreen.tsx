import React, { useMemo, useState } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
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
  },
  {
    id: 's2',
    date: 'Feb 24, 2026',
    wall: 'Lead Wall 1 – 5.10d',
    durationMinutes: 35,
    maxHeight: 13.0,
    clips: 15,
    falls: 0,
  },
];

type Nav = StackNavigationProp<ClimberStackParamList, 'SessionList'>;

export function SessionsScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<Nav>();
  const [wallFilter, setWallFilter] = useState<'all' | 'Lead Wall 1' | 'Lead Wall 2'>('all');

  const filteredSessions = useMemo(() => {
    if (wallFilter === 'all') return SESSIONS;
    return SESSIONS.filter((s) => s.wall.startsWith(wallFilter));
  }, [wallFilter]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('climber.my_sessions')}</Text>
      <View style={styles.filterRow}>
        {(['all', 'Lead Wall 1', 'Lead Wall 2'] as const).map((key) => (
          <TouchableOpacity
            key={key}
            style={[styles.filterChip, wallFilter === key && styles.filterChipActive]}
            onPress={() => setWallFilter(key)}
          >
            <Text
              style={
                wallFilter === key ? styles.filterTextActive : styles.filterText
              }
            >
              {key === 'all' ? 'All walls' : key}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      <FlatList
        data={filteredSessions}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => navigation.navigate('SessionDetail', { sessionId: item.id })}
          >
            <Text style={styles.cardTitle}>{item.wall}</Text>
            <Text style={styles.cardLine}>{item.date}</Text>
            <Text style={styles.cardLine}>
              Duration: {item.durationMinutes} min · Max height: {item.maxHeight.toFixed(1)} m
            </Text>
            <Text style={styles.cardLine}>
              Clips: {item.clips} · Falls: {item.falls}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 12 },
  filterRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  filterChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#ccc',
    marginRight: 8,
  },
  filterChipActive: {
    backgroundColor: '#1a1a2e',
    borderColor: '#1a1a2e',
  },
  filterText: { fontSize: 12, color: '#333' },
  filterTextActive: { fontSize: 12, color: '#fff', fontWeight: '600' },
  card: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    marginBottom: 12,
    backgroundColor: '#fff',
  },
  cardTitle: { fontSize: 16, marginBottom: 4 },
  cardLine: { color: '#444', marginBottom: 2 },
});
