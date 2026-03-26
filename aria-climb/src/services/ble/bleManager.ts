/**
 * BleManager — singleton wrapper around react-native-ble-plx.
 *
 * Responsibilities:
 *   - Scan for ARIA devices (filter by ARIA_SERVICE_UUID or name prefix)
 *   - Connect + subscribe to TELEMETRY notifications
 *   - Write command bytes
 *   - Auto-reconnect on disconnect with exponential backoff
 *
 * All scan/connect results are written to bleStore so UI reacts automatically.
 */

import { BleManager as RNBleManager, Device, State } from 'react-native-ble-plx';
import {
  ARIA_SERVICE_UUID,
  ARIA_CHAR_TELEMETRY,
  ARIA_CHAR_COMMAND,
  ARIA_CHAR_STATUS,
  ARIA_DEVICE_NAME_PREFIX,
} from './bleCharacteristics';
import { parseBlePacket, parseStatusJson } from '../../utils/blePacketParser';
import { useBleStore } from '../../store/bleStore';
import { BLE_SCAN_TIMEOUT_MS, BLE_RECONNECT_DELAY_MS } from '../../utils/constants';

// ─── Singleton ────────────────────────────────────────────────────────────────

let _manager: RNBleManager | null = null;

function getManager(): RNBleManager {
  if (!_manager) {
    _manager = new RNBleManager();
  }
  return _manager;
}

/** Destroy the singleton (call on app unmount / logout). */
export function destroyBleManager(): void {
  _manager?.destroy();
  _manager = null;
}

// ─── Scan ─────────────────────────────────────────────────────────────────────

let _scanTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Start BLE scan.  Discovered ARIA devices are written to bleStore.
 * Automatically stops after BLE_SCAN_TIMEOUT_MS.
 */
export function startScan(): void {
  const manager = getManager();
  const { setScanning, addDiscoveredDevice, setScanError } = useBleStore.getState();

  setScanning(true);
  setScanError(null);

  manager.startDeviceScan(
    [ARIA_SERVICE_UUID],
    { allowDuplicates: false },
    (error, device) => {
      if (error) {
        setScanError(error.message);
        setScanning(false);
        return;
      }
      if (device && (device.name?.startsWith(ARIA_DEVICE_NAME_PREFIX) || device.serviceUUIDs?.includes(ARIA_SERVICE_UUID))) {
        addDiscoveredDevice({
          id: device.id,
          name: device.name ?? device.id,
          rssi: device.rssi ?? -100,
          connected: false,
          gymId: '',
          wallLabel: '',
          lastSeen: Date.now(),
        });
      }
    }
  );

  _scanTimer = setTimeout(() => {
    manager.stopDeviceScan();
    setScanning(false);
  }, BLE_SCAN_TIMEOUT_MS);
}

export function stopScan(): void {
  if (_scanTimer) {
    clearTimeout(_scanTimer);
    _scanTimer = null;
  }
  _manager?.stopDeviceScan();
  useBleStore.getState().setScanning(false);
}

// ─── Connect ──────────────────────────────────────────────────────────────────

const _reconnectTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

/**
 * Connect to an ARIA device by BLE ID.
 * - Reads STATUS characteristic on connect
 * - Subscribes to TELEMETRY notifications
 * - Sets up auto-reconnect on disconnect
 */
export async function connect(deviceId: string): Promise<void> {
  const manager = getManager();
  const { setConnecting, setConnectedDevice, setTelemetry, setConnectionError } =
    useBleStore.getState();

  setConnecting(deviceId, true);
  setConnectionError(null);

  try {
    const device = await manager.connectToDevice(deviceId, { autoConnect: false });
    await device.discoverAllServicesAndCharacteristics();

    // Read initial status
    try {
      const statusChar = await device.readCharacteristicForService(
        ARIA_SERVICE_UUID,
        ARIA_CHAR_STATUS
      );
      if (statusChar.value) {
        const snap = parseStatusJson(
          Buffer.from(statusChar.value, 'base64').toString('utf8')
        );
        if (snap.state) {
          setTelemetry(deviceId, { ...snap, ts: Date.now() } as any);
        }
      }
    } catch {
      // STATUS read is optional
    }

    // Subscribe to telemetry notifications
    device.monitorCharacteristicForService(
      ARIA_SERVICE_UUID,
      ARIA_CHAR_TELEMETRY,
      (error, characteristic) => {
        if (error || !characteristic?.value) return;
        const telemetry = parseBlePacket(characteristic.value);
        if (telemetry) {
          useBleStore.getState().setTelemetry(deviceId, telemetry);
        }
      }
    );

    setConnectedDevice(deviceId);
    setConnecting(deviceId, false);

    // Watch for disconnects and schedule reconnect
    device.onDisconnected((err) => {
      useBleStore.getState().setConnectedDevice(null);
      if (!err) return; // intentional disconnect
      _scheduleReconnect(deviceId, 1);
    });
  } catch (err: any) {
    setConnectionError(err?.message ?? 'Connection failed');
    setConnecting(deviceId, false);
  }
}

function _scheduleReconnect(deviceId: string, attempt: number): void {
  const delay = Math.min(BLE_RECONNECT_DELAY_MS * 2 ** (attempt - 1), 30_000);
  const timer = setTimeout(async () => {
    _reconnectTimers.delete(deviceId);
    try {
      await connect(deviceId);
    } catch {
      _scheduleReconnect(deviceId, attempt + 1);
    }
  }, delay);
  _reconnectTimers.set(deviceId, timer);
}

// ─── Disconnect ───────────────────────────────────────────────────────────────

export async function disconnect(deviceId: string): Promise<void> {
  // Cancel any pending reconnect
  const timer = _reconnectTimers.get(deviceId);
  if (timer) {
    clearTimeout(timer);
    _reconnectTimers.delete(deviceId);
  }
  try {
    await getManager().cancelDeviceConnection(deviceId);
  } catch {
    // ignore — device may already be disconnected
  }
  useBleStore.getState().setConnectedDevice(null);
}

// ─── Commands ─────────────────────────────────────────────────────────────────

export async function sendCommand(deviceId: string, cmdByte: number): Promise<void> {
  const payload = Buffer.from([cmdByte]).toString('base64');
  await getManager().writeCharacteristicWithResponseForDevice(
    deviceId,
    ARIA_SERVICE_UUID,
    ARIA_CHAR_COMMAND,
    payload
  );
}

// ─── BLE state ────────────────────────────────────────────────────────────────

export function onBleStateChange(cb: (state: State) => void): () => void {
  const sub = getManager().onStateChange(cb, true);
  return () => sub.remove();
}
