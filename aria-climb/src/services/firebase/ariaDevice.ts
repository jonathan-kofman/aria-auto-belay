import firestore from '@react-native-firebase/firestore';
import type { FirestoreDevice } from '../../types/device';

const DEVICES = (gymId: string) =>
  firestore().collection('gyms').doc(gymId).collection('devices');

export async function getGymDevice(gymId: string, deviceId: string): Promise<FirestoreDevice | null> {
  const snap = await DEVICES(gymId).doc(deviceId).get();
  if (!snap.exists) return null;
  const data = snap.data()!;
  return {
    deviceId,
    gymId,
    wallName: data.wallName ?? '',
    gradeBand: data.gradeBand ?? '',
    state: data.state ?? 'IDLE',
    firmwareVersion: data.firmwareVersion,
    lastMaintenanceAt: data.lastMaintenanceAt?.toDate?.(),
    lastSeenAt: data.lastSeenAt?.toDate?.(),
  };
}

export function subscribeToGymDevice(
  gymId: string,
  deviceId: string,
  onData: (device: FirestoreDevice | null) => void
): () => void {
  return DEVICES(gymId)
    .doc(deviceId)
    .onSnapshot(
      (snap) => {
        if (!snap.exists) { onData(null); return; }
        const data = snap.data()!;
        onData({
          deviceId,
          gymId,
          wallName: data.wallName ?? '',
          gradeBand: data.gradeBand ?? '',
          state: data.state ?? 'IDLE',
          firmwareVersion: data.firmwareVersion,
          lastMaintenanceAt: data.lastMaintenanceAt?.toDate?.(),
          lastSeenAt: data.lastSeenAt?.toDate?.(),
        });
      },
      () => onData(null)
    );
}

export function subscribeToAllGymDevices(
  gymId: string,
  onData: (devices: FirestoreDevice[]) => void
): () => void {
  return DEVICES(gymId).onSnapshot(
    (snap) => {
      const devices: FirestoreDevice[] = snap.docs.map((d) => {
        const data = d.data();
        return {
          deviceId: d.id,
          gymId,
          wallName: data.wallName ?? '',
          gradeBand: data.gradeBand ?? '',
          state: data.state ?? 'IDLE',
          firmwareVersion: data.firmwareVersion,
          lastMaintenanceAt: data.lastMaintenanceAt?.toDate?.(),
          lastSeenAt: data.lastSeenAt?.toDate?.(),
        };
      });
      onData(devices);
    },
    () => onData([])
  );
}

export interface DeviceCommand {
  deviceId: string;
  gymId: string;
  command: 'ARM' | 'DISARM' | 'ESTOP' | 'RESET_FAULT' | 'MAINTENANCE_LOCK' | 'MAINTENANCE_UNLOCK';
  params: Record<string, unknown>;
  issuedBy: string;
}

/** Write a command to the device's Firestore command queue (ESP32 polls this). */
export async function issueCommand(cmd: DeviceCommand): Promise<void> {
  await DEVICES(cmd.gymId)
    .doc(cmd.deviceId)
    .collection('commands')
    .add({ ...cmd, issuedAt: firestore.FieldValue.serverTimestamp(), acknowledged: false });
}
