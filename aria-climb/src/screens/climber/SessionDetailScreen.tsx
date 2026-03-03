import React, { useEffect, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import firestore from '@react-native-firebase/firestore';
import {
  COLLECTIONS,
  type Session as FsSession,
  type SessionDoc,
  type TensionSample,
} from '../../types/aria';
import type { ClimberStackParamList } from '../../types/navigation';
import { useAuthStore } from '../../store/authStore';
import {
  VictoryAxis,
  VictoryChart,
  VictoryLine,
  VictoryTheme,
  VictoryArea,
  VictoryScatter,
} from 'victory-native';

export function SessionDetailScreen() {
  const route = useRoute<RouteProp<ClimberStackParamList, 'SessionDetail'>>();
  const { sessionId } = route.params;
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'default-gym';

  const [session, setSession] = useState<FsSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!gymId) {
        setLoading(false);
        return;
      }
      try {
        const ref = firestore()
          .collection(COLLECTIONS.sessions(gymId))
          .doc(sessionId);
        const snap = await ref.get();
        if (!snap.exists || cancelled) {
          setLoading(false);
          return;
        }
        const data = snap.data() as SessionDoc;
        const parsed: FsSession = {
          ...data,
          sessionId: snap.id,
          startTime: data.startTime.toDate(),
          endTime: data.endTime ? data.endTime.toDate() : null,
        };
        setSession(parsed);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [gymId, sessionId]);

  const tensionProfile: TensionSample[] = useMemo(
    () => session?.tensionProfile ?? [],
    [session]
  );

  const durationSeconds = useMemo(() => {
    if (!session) return 0;
    const end = session.endTime ?? session.startTime;
    return (end.getTime() - session.startTime.getTime()) / 1000;
  }, [session]);

  const fallCount = session?.fallCount ?? 0;
  const maxHeight = session?.maxHeightMeters ?? 0;
  const clipCount = session?.clipCount ?? 0;

  const fallThreshold = 400; // N — approximate fall detection threshold

  const maxTension = useMemo(
    () => (tensionProfile.length ? Math.max(...tensionProfile.map((p) => p.tension)) : 0),
    [tensionProfile]
  );

  const fallMarkers = useMemo(() => {
    const points: TensionSample[] = [];
    for (let i = 1; i < tensionProfile.length - 1; i += 1) {
      const prev = tensionProfile[i - 1];
      const curr = tensionProfile[i];
      const next = tensionProfile[i + 1];
      if (
        curr.tension > fallThreshold &&
        curr.tension >= prev.tension &&
        curr.tension >= next.tension
      ) {
        points.push(curr);
      }
    }
    return points;
  }, [tensionProfile]);

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Loading session…</Text>
      </View>
    );
  }

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
      <Text style={styles.title}>{session.routeName || session.deviceId}</Text>
      <Text style={styles.line}>
        {session.startTime.toLocaleString()} —{' '}
        {session.endTime ? session.endTime.toLocaleTimeString() : 'active'}
      </Text>
      <Text style={styles.line}>Duration: {durationSeconds.toFixed(1)} s</Text>
      <Text style={styles.line}>Max height: {maxHeight.toFixed(1)} m</Text>
      <Text style={styles.line}>Clips: {clipCount}</Text>
      <Text style={styles.line}>Falls: {fallCount}</Text>

      {tensionProfile.length > 0 ? (
        <View style={{ marginTop: 16 }}>
          <Text style={styles.chartTitle}>Tension over time</Text>
          <VictoryChart
            theme={VictoryTheme.material}
            padding={{ top: 20, left: 50, right: 20, bottom: 40 }}
            height={260}
          >
            <VictoryAxis label="Time (s)" />
            <VictoryAxis dependentAxis label="Tension (N)" />

            {/* Background bands per state (simple overlay by state) */}
            {ORDERED_STATE_BANDS.map(({ state, y }) => {
              const hasState = tensionProfile.some((p) => p.state === state);
              if (!hasState) return null;
              const color = BAND_COLORS[state] || '#f9fafb';
              return (
                <VictoryArea
                  key={state}
                  data={[
                    { x: 0, y: 0 },
                    { x: tensionProfile[tensionProfile.length - 1].t, y: 0 },
                  ]}
                  style={{
                    data: { fill: color, opacity: 0.1 },
                  }}
                />
              );
            })}

            {/* Tension line */}
            <VictoryLine
              data={tensionProfile}
              x="t"
              y="tension"
              style={{ data: { stroke: '#1f2937', strokeWidth: 2 } }}
            />

            {/* Fall markers */}
            {fallMarkers.length > 0 && (
              <VictoryScatter
                data={fallMarkers}
                x="t"
                y="tension"
                size={4}
                style={{ data: { fill: '#b91c1c' } }}
              />
            )}
          </VictoryChart>
        </View>
      ) : (
        <Text style={[styles.line, { marginTop: 12 }]}>
          No tension data recorded for this session.
        </Text>
      )}
    </View>
  );
}

const ORDERED_STATE_BANDS: { state: ARIAState; y: number }[] = [
  { state: 'IDLE', y: 0 },
  { state: 'CLIMBING', y: 1 },
  { state: 'CLIPPING', y: 2 },
  { state: 'TAKE', y: 3 },
  { state: 'REST', y: 4 },
  { state: 'LOWER', y: 5 },
  { state: 'WATCH_ME', y: 6 },
  { state: 'UP', y: 7 },
  { state: 'FAULT', y: 8 },
  { state: 'LOCKOUT', y: 9 },
  { state: 'MAINTENANCE', y: 10 },
];

const BAND_COLORS: Partial<Record<ARIAState, string>> = {
  IDLE: '#e5e7eb',
  CLIMBING: '#bbf7d0',
  CLIPPING: '#bfdbfe',
  TAKE: '#fef9c3',
  REST: '#e9d5ff',
  LOWER: '#bae6fd',
  WATCH_ME: '#fed7aa',
  UP: '#c7d2fe',
  FAULT: '#fecaca',
  LOCKOUT: '#fecaca',
  MAINTENANCE: '#fef3c7',
};

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 8 },
  line: { color: '#444', marginBottom: 4 },
  chartTitle: { fontSize: 16, fontWeight: '600', marginBottom: 4 },
});
