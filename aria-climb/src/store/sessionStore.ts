// TODO: Phase 3
import { create } from 'zustand';
import type { Session, TensionSample, HeightSample, SessionEvent } from '../types/session';

interface SessionState {
  currentSession: Partial<Session> | null;
  tensionBuffer: TensionSample[];
  heightBuffer: HeightSample[];
  eventBuffer: SessionEvent[];
  startSession: (deviceId: string, climberId: string) => void;
  endSession: () => Promise<void>;
  addTensionSample: (sample: TensionSample) => void;
  addEvent: (event: SessionEvent) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  currentSession: null,
  tensionBuffer: [],
  heightBuffer: [],
  eventBuffer: [],
  startSession: (deviceId, climberId) =>
    set({
      currentSession: { deviceId, climberId },
      tensionBuffer: [],
      heightBuffer: [],
      eventBuffer: [],
    }),
  endSession: async () =>
    set({
      currentSession: null,
      tensionBuffer: [],
      heightBuffer: [],
      eventBuffer: [],
    }),
  addTensionSample: (sample) =>
    set((s) => ({ tensionBuffer: [...s.tensionBuffer, sample] })),
  addEvent: (event) =>
    set((s) => ({ eventBuffer: [...s.eventBuffer, event] })),
}));
