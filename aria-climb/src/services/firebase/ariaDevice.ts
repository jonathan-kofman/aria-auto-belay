import firestore from '@react-native-firebase/firestore';
import { ARIADeviceDoc, ARIADeviceState, CommandDoc, MaintenanceLogDoc, COLLECTIONS } from '../../types/aria';

const STALE_THRESHOLD_MS = 30_000;

function parseDevice(doc: ARIADeviceDoc): ARIADeviceState {
  const lastHeartbeat = doc.lastHeartbeat.toDate();
  const now = new Date();
  return {
    ...doc,
    lastHeartbeat,
    installDate: doc.installDate.toDate(),
    nextInspectionDue: doc.nextInspectionDue.toDate(),
    lastMaintenanceAt: doc.lastMaintenanceAt?.toDate() ?? null,
    isStale: now.getTime() - lastHeartbeat.getTime() > STALE_THRESHOLD_MS,
    needsInspection: doc.nextInspectionDue.toDate() <= now,
  };
}

/** Real-time listener for a single device */
export function subscribeToDevice(
  gymId: string,
  deviceId: string,
  onUpdate: (device: ARIADeviceState) => void,
  onError: (err: Error) => void
): () => void {
  return firestore()
    .doc(COLLECTIONS.device(gymId, deviceId))
    .onSnapshot(
      snap => {
        if (!snap.exists) return;
        onUpdate(parseDevice(snap.data() as ARIADeviceDoc));
      },
      onError
    );
}

/** Real-time listener for all devices in a gym */
export function subscribeToAllDevices(
  gymId: string,
  onUpdate: (devices: ARIADeviceState[]) => void,
  onError: (err: Error) => void
): () => void {
  return firestore()
    .collection(COLLECTIONS.devices(gymId))
    .onSnapshot(
      snap => {
        const devices = snap.docs.map(d => parseDevice(d.data() as ARIADeviceDoc));
        onUpdate(devices);
      },
      onError
    );
}

/** Issue a maintenance command to a device */
export async function issueCommand(
  command: Omit<CommandDoc, 'commandId' | 'acknowledged' | 'acknowledgedAt' | 'result' | 'errorMessage'>
): Promise<string> {
  const ref = firestore()
    .collection(COLLECTIONS.commands)
    .doc(command.deviceId);

  const commandId = firestore().collection('_').doc().id; // generate ID

  await ref.set({
    ...command,
    commandId,
    acknowledged: false,
    acknowledgedAt: null,
    result: 'PENDING',
    errorMessage: null,
  });

  return commandId;
}

/** Write a maintenance log entry */
export async function logMaintenance(
  entry: Omit<MaintenanceLogDoc, 'logId'>
): Promise<void> {
  const ref = firestore()
    .collection(COLLECTIONS.maintenanceLogs(entry.gymId))
    .doc();

  await ref.set({ ...entry, logId: ref.id });
}

/** One-time fetch of device health summary (for inspection reports) */
export async function getDeviceHealthSnapshot(
  gymId: string,
  deviceId: string
): Promise<ARIADeviceState | null> {
  const snap = await firestore()
    .doc(COLLECTIONS.device(gymId, deviceId))
    .get();

  if (!snap.exists) return null;
  return parseDevice(snap.data() as ARIADeviceDoc);
}