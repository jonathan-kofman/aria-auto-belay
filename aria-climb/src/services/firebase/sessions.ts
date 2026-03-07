import firestore from '@react-native-firebase/firestore';
import { useEffect, useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import type { Session as StoreSession, TensionSample, SessionEvent } from '../../types/session';
import { COLLECTIONS, type SessionDoc, type Session as FirestoreSession } from '../../types/aria';

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

function fromDoc(id: string, d: FirestoreSessionDoc): StoreSession {
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
  onUpdate: (sessions: StoreSession[]) => void,
  onError: (err: Error) => void
): () => void {
  return sessionsCol(gymId)
    .where('endTime', '==', null)
    .onSnapshot(
      (snap) => {
        const sessions: StoreSession[] = [];
        snap.forEach((docSnap) => {
          const data = docSnap.data() as FirestoreSessionDoc;
          sessions.push(fromDoc(docSnap.id, data));
        });
        onUpdate(sessions);
      },
      (err) => onError(err as Error)
    );
}

export function useActiveSession() {
  const user = useAuthStore((s) => s.user);
  const [sessions, setSessions] = useState<StoreSession[]>([]);
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

function parseSession(doc: SessionDoc): FirestoreSession {
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

