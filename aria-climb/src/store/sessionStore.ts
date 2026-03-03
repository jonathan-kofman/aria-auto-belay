// TODO: Phase 3
import { create } from 'zustand';
import type { Session, TensionSample, HeightSample, SessionEvent } from '../types/session';
import * as sessionService from '../services/firebase/sessions';

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
    try {
      const id = await sessionService.startSession(deviceId, routeName);
      return id;
    } catch {
      return null;
    }
  },
  endSession: async () => {
    await sessionService.endSession();
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
