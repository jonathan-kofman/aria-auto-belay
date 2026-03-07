import { create } from 'zustand';
import firestore from '@react-native-firebase/firestore';
import { useAuthStore } from './authStore';
import type { Session, TensionSample, HeightSample, SessionEvent } from '../types/session';

type FirebaseTimestamp = typeof import('@react-native-firebase/firestore')['Timestamp'];

type FirestoreSessionDoc = {
  deviceId: string;
  climberId: string;
  climberName: string;
  gymId: string;
  routeName?: string | null;
  startTime: FirebaseTimestamp['prototype'];
  endTime?: FirebaseTimestamp['prototype'] | null;
  durationSeconds?: number | null;
  maxHeightMeters?: number | null;
  clipCount?: number | null;
  fallCount?: number | null;
  tensionTrace?: TensionSample[];
  heightTrace?: { t: number; height: number }[];
  events?: SessionEvent[];
};

function sessionsCol(gymId: string) {
  return firestore().collection(`gyms/${gymId}/sessions`);
}

interface SessionState {
  currentSession: Partial<Session> | null;
  tensionBuffer: TensionSample[];
  heightBuffer: HeightSample[];
  eventBuffer: SessionEvent[];
  startSession: (deviceId: string, routeName?: string) => Promise<string | null>;
  endSession: () => Promise<void>;
  addTensionSample: (sample: TensionSample) => void;
  addEvent: (event: SessionEvent) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  currentSession: null,
  tensionBuffer: [],
  heightBuffer: [],
  eventBuffer: [],
  startSession: async (deviceId, routeName) => {
    const user = useAuthStore.getState().user;
    if (!user) return null;
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
    set({
      currentSession: {
        id: ref.id,
        gymId,
        deviceId,
        climberId: user.uid,
        climberName: user.displayName,
      },
      tensionBuffer: [],
      heightBuffer: [],
      eventBuffer: [],
    });
    return ref.id;
  },
  endSession: async () => {
    const state = useSessionStore.getState();
    const { currentSession, tensionBuffer, heightBuffer, eventBuffer } = state;
    const user = useAuthStore.getState().user;
    if (!currentSession || !user || !currentSession.gymId) {
      set({
        currentSession: null,
        tensionBuffer: [],
        heightBuffer: [],
        eventBuffer: [],
      });
      return;
    }
    const gymId = currentSession.gymId as string;
    const sessionId = currentSession.id as string;
    const ref = sessionsCol(gymId).doc(sessionId);
    const docSnap = await ref.get();
    if (!docSnap.exists) {
      set({
        currentSession: null,
        tensionBuffer: [],
        heightBuffer: [],
        eventBuffer: [],
      });
      return;
    }
    const existing = docSnap.data() as FirestoreSessionDoc;
    const start = existing.startTime.toDate();
    const end = new Date();
    const durationSeconds = (end.getTime() - start.getTime()) / 1000;
    const maxHeightMeters = Math.max(
      existing.maxHeightMeters ?? 0,
      ...((existing.heightTrace ?? []).map((h) => h.height) || []),
      ...heightBuffer.map((h) => h.height),
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
        heightTrace: [...(existing.heightTrace ?? []), ...heightBuffer],
        events: [...(existing.events ?? []), ...eventBuffer],
      },
      { merge: true }
    );

    set({
      currentSession: null,
      tensionBuffer: [],
      heightBuffer: [],
      eventBuffer: [],
    });
  },
  addTensionSample: (sample) =>
    set((s) => ({ tensionBuffer: [...s.tensionBuffer, sample] })),
  addEvent: (event) =>
    set((s) => ({ eventBuffer: [...s.eventBuffer, event] })),
}));
