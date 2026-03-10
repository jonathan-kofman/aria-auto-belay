/**
 * Store for safety monitoring test state (mock zone intrusion, etc.).
 * Used by Safety / Camera test screen and AlertBanner so the full flow works without hardware.
 */
import { create } from 'zustand';

interface SafetyTestState {
  mockZoneIntrusionActive: boolean;
  setMockZoneIntrusion: (active: boolean) => void;
}

export const useSafetyTestStore = create<SafetyTestState>((set) => ({
  mockZoneIntrusionActive: false,
  setMockZoneIntrusion: (active) => set({ mockZoneIntrusionActive: active }),
}));
