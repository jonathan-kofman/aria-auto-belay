/**
 * useARIADevice — unified hook covering two call signatures:
 *
 *   Climber (BLE):  useARIADevice(deviceId)
 *     → { telemetry, connected, connecting, connectionError, connect, disconnect, arm, disarm, resetFault }
 *
 *   Gym (Firestore): useARIADevice(gymId, deviceId)
 *     → { device, isLoading, telemetry, connected, ... }
 */

import { useCallback, useEffect, useState } from 'react';
import { useBleStore } from '../store/bleStore';
import {
  connect as bleConnect,
  disconnect as bleDisconnect,
  sendCommand,
} from '../services/ble/bleManager';
import { subscribeToGymDevice } from '../services/firebase/ariaDevice';
import { CMD } from '../services/ble/bleCharacteristics';
import type { ARIATelemetry } from '../types/aria';
import type { FirestoreDevice } from '../types/device';

// ─── BLE-only hook (climber) ─────────────────────────────────────────────────

interface BLEResult {
  device?: undefined;
  isLoading?: false;
  telemetry: ARIATelemetry | null;
  connected: boolean;
  connecting: boolean;
  connectionError: string | null;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  arm: () => Promise<void>;
  disarm: () => Promise<void>;
  resetFault: () => Promise<void>;
}

// ─── Firestore + optional BLE hook (gym) ────────────────────────────────────

interface GymResult {
  device: FirestoreDevice | null;
  isLoading: boolean;
  telemetry: ARIATelemetry | null;
  connected: boolean;
  connecting: boolean;
  connectionError: string | null;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  arm: () => Promise<void>;
  disarm: () => Promise<void>;
  resetFault: () => Promise<void>;
}

// ─── Overloads ────────────────────────────────────────────────────────────────

export function useARIADevice(deviceId: string): BLEResult;
export function useARIADevice(gymId: string, deviceId: string): GymResult;
export function useARIADevice(gymIdOrDeviceId: string, maybeDeviceId?: string): BLEResult | GymResult {
  const isGymMode = maybeDeviceId !== undefined;
  const gymId = isGymMode ? gymIdOrDeviceId : '';
  const deviceId = isGymMode ? maybeDeviceId! : gymIdOrDeviceId;

  // BLE state
  const connectedDeviceId = useBleStore((s) => s.connectedDeviceId);
  const connectingMap = useBleStore((s) => s.connecting);
  const connectionError = useBleStore((s) => s.connectionError);
  const telemetryMap = useBleStore((s) => s.telemetry);

  const connected = connectedDeviceId === deviceId;
  const connecting = connectingMap[deviceId] ?? false;
  const telemetry = telemetryMap[deviceId] ?? null;

  // Firestore device (gym mode only)
  const [device, setDevice] = useState<FirestoreDevice | null>(null);
  const [isLoading, setIsLoading] = useState(isGymMode);

  useEffect(() => {
    if (!isGymMode || !gymId || !deviceId) { setIsLoading(false); return; }
    setIsLoading(true);
    const unsub = subscribeToGymDevice(gymId, deviceId, (d) => {
      setDevice(d);
      setIsLoading(false);
    });
    return unsub;
  }, [isGymMode, gymId, deviceId]);

  // Auto-disconnect BLE on unmount
  useEffect(() => {
    return () => {
      if (connected) bleDisconnect(deviceId).catch(() => {});
    };
  }, [connected, deviceId]);

  const connectFn = useCallback(() => bleConnect(deviceId), [deviceId]);
  const disconnectFn = useCallback(() => bleDisconnect(deviceId), [deviceId]);
  const arm = useCallback(() => sendCommand(deviceId, CMD.ARM), [deviceId]);
  const disarm = useCallback(() => sendCommand(deviceId, CMD.DISARM), [deviceId]);
  const resetFault = useCallback(() => sendCommand(deviceId, CMD.RESET_FAULT), [deviceId]);

  if (isGymMode) {
    return { device, isLoading, telemetry, connected, connecting, connectionError, connect: connectFn, disconnect: disconnectFn, arm, disarm, resetFault };
  }
  return { telemetry, connected, connecting, connectionError, connect: connectFn, disconnect: disconnectFn, arm, disarm, resetFault };
}
