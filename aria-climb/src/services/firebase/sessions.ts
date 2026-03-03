import firestore from '@react-native-firebase/firestore';
import { useEffect, useState } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { useAuthStore } from '../../store/authStore';
import type { Session, TensionSample, SessionEvent } from '../../types/session';

type FirestoreSessionDoc = {
  deviceId: string;
  climberId: string;
  climberName: string;
  gymId: string;
  routeName?: string | null;
  startTime: FirebaseFirestoreTypes.Timestamp;
  endTime?: FirebaseFirestoreTypes.Timestamp | null;
  durationSeconds?: number | null;
  maxHeightMeters?: number | null;
  clipCount?: number | null;
  fallCount?: number | null;
  tensionTrace?: TensionSample[];
  heightTrace?: { t: number; height: number }[];
  events?: SessionEvent[];
};

type FirebaseFirestoreTypes = typeof import('@react-native-firebase/firestore');

function sessionsCol(gymId: string) {
  return firestore().collection(`gyms/${gymId}/sessions`);
}

function fromDoc(id: string, d: FirestoreSessionDoc): Session {
  return {
    id,
    gymId: d.gymId,
    deviceId: d.deviceId,
    climberId: d.climberId,
    climberName: d.climberName,
    routeName: d.routeName ?? '',
    startTime: d.startTime.toDate(),
    endTime: d.endTime ? d.endTime.toDate() : d.startTime.toDate(),
    durationSeconds: d.durationSeconds ?? 0,
    maxHeightMeters: d.maxHeightMeters ?? 0,
    clipCount: d.clipCount ?? 0,
    fallCount: d.fallCount ?? 0,
    tensionTrace: d.tensionTrace ?? [],
    heightTrace: (d.heightTrace ?? []).map((h) => ({ t: h.t, height: h.height })),
    events: d.events ?? [],
  };
}

export function subscribeToActiveSessions(
  gymId: string,
  onUpdate: (sessions: Session[]) => void,
  onError: (err: Error) => void
): () => void {
  return sessionsCol(gymId)
    .where('endTime', '==', null)
    .onSnapshot(
      (snap) => {
        const sessions: Session[] = [];
        snap.forEach((docSnap) => {
          const data = docSnap.data() as FirestoreSessionDoc;
          sessions.push(fromDoc(docSnap.id, data));
        });
        onUpdate(sessions);
      },
      (err) => onError(err as Error)
    );
}

export async function startSession(deviceId: string, routeName?: string): Promise<string> {
  const user = useAuthStore.getState().user;
  if (!user) {
    throw new Error('Not authenticated');
  }
  const gymId = user.homeGymId || 'default-gym';
  const col = sessionsCol(gymId);
  const ref = col.doc();
  const now = firestore.FieldValue.serverTimestamp();
  await ref.set({
    gymId,
    deviceId,
    climberId: user.uid,
    climberName: user.displayName,
    routeName: routeName ?? null,
    startTime: now,
    endTime: null,
    durationSeconds: null,
    maxHeightMeters: 0,
    clipCount: 0,
    fallCount: 0,
    tensionTrace: [],
    heightTrace: [],
    events: [],
  });
  useSessionStore.setState({
    currentSession: { id: ref.id, deviceId, climberId: user.uid, climberName: user.displayName, gymId },
    tensionBuffer: [],
    heightBuffer: [],
    eventBuffer: [],
  });
  return ref.id;
}

export async function endSession(): Promise<void> {
  const { currentSession, tensionBuffer, heightBuffer, eventBuffer } = useSessionStore.getState();
  const user = useAuthStore.getState().user;
  if (!currentSession || !user || !currentSession.gymId) return;
  const gymId = currentSession.gymId;
  const sessionId = currentSession.id as string;
  const ref = sessionsCol(gymId).doc(sessionId);
  const doc = await ref.get();
  if (!doc.exists) return;
  const existing = doc.data() as FirestoreSessionDoc;

  const start = existing.startTime.toDate();
  const end = new Date();
  const durationSeconds = (end.getTime() - start.getTime()) / 1000;
  const maxHeightMeters = Math.max(
    existing.maxHeightMeters ?? 0,
    ...((existing.heightTrace ?? []).map((h) => h.height) || []),
    ...tensionBuffer.map(() => 0) // keep types happy; real height updates via heightBuffer
  );
  const clipCount = (existing.clipCount ?? 0) + eventBuffer.filter((e) => e.type === 'clip').length;
  const fallCount =
    (existing.fallCount ?? 0) + eventBuffer.filter((e) => e.type === 'fall').length;

  await ref.set(
    {
      endTime: firestore.FieldValue.serverTimestamp(),
      durationSeconds,
      maxHeightMeters,
      clipCount,
      fallCount,
      tensionTrace: [...(existing.tensionTrace ?? []), ...tensionBuffer],
      heightTrace: [...(existing.heightTrace ?? []), ...useSessionStore.getState().heightBuffer],
      events: [...(existing.events ?? []), ...eventBuffer],
    },
    { merge: true }
  );

  useSessionStore.setState({
    currentSession: null,
    tensionBuffer: [],
    heightBuffer: [],
    eventBuffer: [],
  });
}

export async function addTensionSample(sample: TensionSample): Promise<void> {
  useSessionStore.getState().addTensionSample(sample);
}

export async function addEvent(event: SessionEvent): Promise<void> {
  useSessionStore.getState().addEvent(event);
}

export function useActiveSession() {
  const user = useAuthStore((s) => s.user);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!user?.homeGymId) {
      setSessions([]);
      setLoading(false);
      return;
    }
    const unsub = subscribeToActiveSessions(
      user.homeGymId,
      (list) => {
        setSessions(list);
        setLoading(false);
      },
      (err) => {
        setError(err);
        setLoading(false);
      }
    );
    return unsub;
  }, [user?.homeGymId]);

  return { sessions, loading, error };
}

import firestore from '@react-native-firebase/firestore';
import { COLLECTIONS, SessionDoc, Session } from '../../types/aria';

function parseSession(doc: SessionDoc): Session {
  return {
    ...doc,
    startTime: doc.startTime.toDate(),
    endTime: doc.endTime ? doc.endTime.toDate() : null,
  };
}

export function subscribeToSessions(
  gymId: string,
  onUpdate: (sessions: Session[]) => void,
  onError: (err: Error) => void,
  limitTo = 100
): () => void {
  return firestore()
    .collection(COLLECTIONS.sessions(gymId))
    .orderBy('startTime', 'desc')
    .limit(limitTo)
    .onSnapshot(
      snap => onUpdate(snap.docs.map(d => parseSession(d.data() as SessionDoc))),
      onError
    );
}

