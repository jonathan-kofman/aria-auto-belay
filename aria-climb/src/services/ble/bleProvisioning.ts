import { BleManager, Device, State } from 'react-native-ble-plx';
import { Buffer } from 'buffer';

// These UUIDs you'll also define in ESP32 firmware — keep them in sync
export const PROVISIONING_SERVICE_UUID = '4fafc201-1fb5-459e-8fcc-c5c9c331914b';
export const WIFI_CHAR_UUID           = 'beb5483e-36e1-4688-b7f5-ea07361b26a8';
export const GYM_CHAR_UUID            = 'beb5483f-36e1-4688-b7f5-ea07361b26a8';
export const STATUS_CHAR_UUID         = 'beb54840-36e1-4688-b7f5-ea07361b26a8';

export type ProvisioningStatus =
  | 'IDLE'
  | 'SCANNING'
  | 'CONNECTING'
  | 'SENDING_WIFI'
  | 'SENDING_GYM'
  | 'WAITING_REBOOT'
  | 'VERIFYING_ONLINE'
  | 'SUCCESS'
  | 'FAILED';

export interface ARIAAdvertisedDevice {
  bleDevice: Device;
  deviceId: string;   // aria_a1b2c3
  macSuffix: string;  // A1B2C3
  rssi: number;
}

export interface ProvisioningPayload {
  ssid: string;
  password: string;   // TODO: encrypt before production
  gymId: string;
  deviceId: string;
}

const manager = new BleManager();

/** Scan for unprovisioned ARIA devices (advertising "ARIA-" prefix) */
export function scanForARIADevices(
  onFound: (device: ARIAAdvertisedDevice) => void,
  onError: (err: Error) => void,
  timeoutMs = 15_000
): () => void {
  let stopped = false;

  manager.state().then(state => {
    if (state !== State.PoweredOn) {
      onError(new Error('Bluetooth is not enabled'));
      return;
    }

    manager.startDeviceScan(
      [PROVISIONING_SERVICE_UUID],
      { allowDuplicates: false },
      (err, device) => {
        if (err) { onError(err); return; }
        if (!device || !device.name?.startsWith('ARIA-')) return;

        const macSuffix = device.name.replace('ARIA-', '');
        onFound({
          bleDevice: device,
          deviceId: `aria_${macSuffix.toLowerCase()}`,
          macSuffix,
          rssi: device.rssi ?? -99,
        });
      }
    );

    setTimeout(() => {
      if (!stopped) manager.stopDeviceScan();
    }, timeoutMs);
  });

  return () => {
    stopped = true;
    manager.stopDeviceScan();
  };
}

/** Full provisioning sequence — call this after user selects a device */
export async function provisionDevice(
  advertised: ARIAAdvertisedDevice,
  payload: ProvisioningPayload,
  onStatus: (status: ProvisioningStatus) => void
): Promise<boolean> {
  let device: Device | null = null;

  try {
    onStatus('CONNECTING');
    device = await manager.connectToDevice(advertised.bleDevice.id);
    await device.discoverAllServicesAndCharacteristics();

    // Write WiFi credentials
    onStatus('SENDING_WIFI');
    const wifiJson = JSON.stringify({ ssid: payload.ssid, password: payload.password });
    await device.writeCharacteristicWithResponseForService(
      PROVISIONING_SERVICE_UUID,
      WIFI_CHAR_UUID,
      Buffer.from(wifiJson).toString('base64')
    );

    // Write gym + device registration
    onStatus('SENDING_GYM');
    const gymJson = JSON.stringify({ gymId: payload.gymId, deviceId: payload.deviceId });
    await device.writeCharacteristicWithResponseForService(
      PROVISIONING_SERVICE_UUID,
      GYM_CHAR_UUID,
      Buffer.from(gymJson).toString('base64')
    );

    // Read status char — ESP32 responds with "OK" or "ERR"
    const statusChar = await device.readCharacteristicForService(
      PROVISIONING_SERVICE_UUID,
      STATUS_CHAR_UUID
    );
    const statusVal = Buffer.from(statusChar.value ?? '', 'base64').toString('utf8');
    if (statusVal !== 'OK') throw new Error(`ESP32 rejected config: ${statusVal}`);

    onStatus('WAITING_REBOOT');
    await device.cancelConnection();
    device = null;

    return true;
  } catch (err) {
    onStatus('FAILED');
    if (device) {
      try { await device.cancelConnection(); } catch {}
    }
    console.error('[BLE Provisioning]', err);
    return false;
  }
}