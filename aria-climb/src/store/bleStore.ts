// TODO: Phase 2
import { create } from 'zustand';
import type { ARIADevice } from '../types/device';

interface BLEState {
  devices: Record<string, ARIADevice>;
  isScanning: boolean;
  updateDevice: (deviceId: string, patch: Partial<ARIADevice>) => void;
  removeDevice: (deviceId: string) => void;
}

export const useBLEStore = create<BLEState>((set) => ({
  devices: {},
  isScanning: false,
  updateDevice: (deviceId, patch) =>
    set((s) => ({
      devices: {
        ...s.devices,
        [deviceId]: { ...(s.devices[deviceId] ?? ({} as ARIADevice)), ...patch },
      },
    })),
  removeDevice: (deviceId) =>
    set((s) => {
      const next = { ...s.devices };
      delete next[deviceId];
      return { devices: next };
    }),
}));
