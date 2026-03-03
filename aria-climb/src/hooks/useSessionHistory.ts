import { useEffect, useState } from 'react';
import firestore from '@react-native-firebase/firestore';
import { COLLECTIONS, type Session as FsSession, type SessionDoc } from '../types/aria';
import { useAuthStore } from '../store/authStore';

type Mode = 'climber' | 'gym';

interface UseSessionHistoryOptions {
  mode?: Mode;
  limit?: number;
}

function fromDoc(id: string, d: SessionDoc): FsSession {
  return {
    ...d,
    sessionId: id,
    startTime: d.startTime.toDate(),
    endTime: d.endTime ? d.endTime.toDate() : null,
  };
}

// Firestore query hook for session list
export function useSessionHistory(
  gymIdOverride?: string,
  deviceId?: string,
  options: UseSessionHistoryOptions = {}
) {
  const { mode = 'climber', limit = 50 } = options;
  const user = useAuthStore((s) => s.user);
  const [sessions, setSessions] = useState<FsSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const gymId = gymIdOverride || user?.homeGymId;
    if (!gymId) {
      setSessions([]);
      setLoading(false);
      return;
    }

    let query: FirebaseFirestoreTypes.Query = firestore()
      .collection(COLLECTIONS.sessions(gymId))
      .orderBy('startTime', 'desc')
      .limit(limit);

    if (mode === 'climber' && user) {
      query = query.where('climberId', '==', user.uid);
    }

    if (deviceId) {
      query = query.where('deviceId', '==', deviceId);
    }

    const unsub = query.onSnapshot(
      (snap) => {
        const next: FsSession[] = [];
        snap.forEach((docSnap) => {
          const data = docSnap.data() as SessionDoc;
          next.push(fromDoc(docSnap.id, data));
        });
        setSessions(next);
        setLoading(false);
      },
      (err) => {
        setError(err as Error);
        setLoading(false);
      }
    );

    return unsub;
  }, [gymIdOverride, deviceId, limit, mode, user?.homeGymId, user?.uid]);

  return { sessions, loading, error };
}
