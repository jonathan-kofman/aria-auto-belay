/**
 * Zustand store for BLE state — discovered devices, connection status, telemetry.
 */

import { create } from 'zustand';
import type { ARIADevice, ARIATelemetry } from '../types/aria';

interface BleState {
  /** Whether a scan is active */
  scanning: boolean;
  /** Error from last scan, if any */
  scanError: string | null;
  /** Discovered devices keyed by BLE device ID */
  discoveredDevices: Record<string, ARIADevice>;
  /** BLE ID of the currently connected device, or null */
  connectedDeviceId: string | null;
  /** Whether a connection attempt is in progress */
  connecting: Record<string, boolean>;
  /** Connection error from last connect attempt */
  connectionError: string | null;
  /** Latest telemetry per device ID */
  telemetry: Record<string, ARIATelemetry>;

  // Actions
  setScanning: (v: boolean) => void;
  setScanError: (e: string | null) => void;
  addDiscoveredDevice: (device: ARIADevice) => void;
  setConnectedDevice: (id: string | null) => void;
  setConnecting: (id: string, v: boolean) => void;
  setConnectionError: (e: string | null) => void;
  setTelemetry: (id: string, t: ARIATelemetry) => void;
  clearDiscovered: () => void;
}

export const useBleStore = create<BleState>((set) => ({
  scanning: false,
  scanError: null,
  discoveredDevices: {},
  connectedDeviceId: null,
  connecting: {},
  connectionError: null,
  telemetry: {},

  setScanning: (v) => set({ scanning: v }),
  setScanError: (e) => set({ scanError: e }),

  addDiscoveredDevice: (device) =>
    set((s) => ({
      discoveredDevices: {
        ...s.discoveredDevices,
        [device.id]: { ...s.discoveredDevices[device.id], ...device },
      },
    })),

  setConnectedDevice: (id) => set({ connectedDeviceId: id }),

  setConnecting: (id, v) =>
    set((s) => ({ connecting: { ...s.connecting, [id]: v } })),

  setConnectionError: (e) => set({ connectionError: e }),

  setTelemetry: (id, t) =>
    set((s) => ({ telemetry: { ...s.telemetry, [id]: t } })),

  clearDiscovered: () => set({ discoveredDevices: {} }),
}));
