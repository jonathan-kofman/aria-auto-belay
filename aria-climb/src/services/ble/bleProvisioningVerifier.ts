import firestore from '@react-native-firebase/firestore';
import { COLLECTIONS } from '../../types/aria';

/**
 * After ESP32 reboots and connects to WiFi it will write its first heartbeat.
 * We watch for that document to appear with isOnline: true.
 */
export function waitForDeviceOnline(
  gymId: string,
  deviceId: string,
  onOnline: () => void,
  onTimeout: () => void,
  timeoutMs = 60_000   // 60s — ESP32 boot + WiFi connect + first push
): () => void {
  let timedOut = false;

  const timer = setTimeout(() => {
    timedOut = true;
    unsub();
    onTimeout();
  }, timeoutMs);

  const unsub = firestore()
    .doc(COLLECTIONS.device(gymId, deviceId))
    .onSnapshot(snap => {
      if (timedOut) return;
      if (snap.exists && snap.data()?.isOnline === true) {
        clearTimeout(timer);
        unsub();
        onOnline();
      }
    });

  return () => {
    clearTimeout(timer);
    unsub();
  };
}