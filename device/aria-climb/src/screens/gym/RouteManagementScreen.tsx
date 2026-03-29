import React, { useState } from 'react';
import { View, Text, FlatList, Switch, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

type RouteRow = {
  id: string;
  wall: string;
  name: string;
  grade: string;
  active: boolean;
};

const INITIAL_ROUTES: RouteRow[] = [
  { id: 'r1', wall: 'Lead Wall 1', name: 'Warmup arete', grade: '5.10c', active: true },
  { id: 'r2', wall: 'Lead Wall 2', name: 'Techy face', grade: '5.11b', active: true },
  { id: 'r3', wall: 'Training Wall', name: 'Endurance laps', grade: '5.10a', active: false },
];

export function RouteManagementScreen() {
  const { t } = useTranslation();
  const [routes, setRoutes] = useState<RouteRow[]>(INITIAL_ROUTES);

  function toggleRoute(id: string) {
    setRoutes((prev) => prev.map((r) => (r.id === id ? { ...r, active: !r.active } : r)));
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('gym.routes')}</Text>
      <FlatList
        data={routes}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View style={styles.info}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.line}>
                {item.wall} · {item.grade}
              </Text>
            </View>
            <View style={styles.toggleCol}>
              <Text style={styles.toggleLabel}>{item.active ? 'Active' : 'Hidden'}</Text>
              <Switch value={item.active} onValueChange={() => toggleRoute(item.id)} />
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 12 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  info: { flex: 1 },
  name: { fontSize: 14, fontWeight: '500' },
  line: { color: '#444', fontSize: 12, marginTop: 2 },
  toggleCol: { alignItems: 'center' },
  toggleLabel: { fontSize: 12, color: '#666', marginBottom: 4 },
});
