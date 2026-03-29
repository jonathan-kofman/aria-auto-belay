import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

const LEADERS = [
  { rank: 1, name: 'Alex', bestGrade: '5.12a', metersClimbed: 420 },
  { rank: 2, name: 'Maya', bestGrade: '5.11d', metersClimbed: 380 },
  { rank: 3, name: 'Jon', bestGrade: '5.11c', metersClimbed: 350 },
  { rank: 4, name: 'Demo climber', bestGrade: '5.11b', metersClimbed: 300 },
];

export function LeaderboardScreen() {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('climber.leaderboard')}</Text>
      <Text style={styles.subtitle}>This week at your home gym</Text>
      {LEADERS.map((entry) => (
        <View key={entry.rank} style={styles.row}>
          <Text style={styles.rank}>{entry.rank}</Text>
          <View style={styles.info}>
            <Text style={styles.name}>{entry.name}</Text>
            <Text style={styles.detail}>
              Best: {entry.bestGrade} · {entry.metersClimbed} m climbed
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 4 },
  subtitle: { color: '#666', marginBottom: 12 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  rank: { width: 28, fontSize: 18, fontWeight: '600' },
  info: { flex: 1 },
  name: { fontSize: 16 },
  detail: { color: '#444', marginTop: 2 },
});
