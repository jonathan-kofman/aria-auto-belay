import { useEffect, useState } from 'react';
import { ARIADeviceState } from '../types/aria';
import { subscribeToAllDevices } from '../services/firebase/ariaDevice';

export function useGymDevices(gymId: string) {
  const [devices, setDevices] = useState<ARIADeviceState[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!gymId) return;

    const unsub = subscribeToAllDevices(
      gymId,
      (devs) => {
        setDevices(devs);
        setIsLoading(false);
      },
      (err) => {
        setError(err);
        setIsLoading(false);
      }
    );

    return unsub;
  }, [gymId]);

  // Derived summaries for DashboardScreen
  const summary = {
    total: devices.length,
    active: devices.filter(d => d.isOnline && !d.isLocked && !d.isInMaintenance).length,
    offline: devices.filter(d => !d.isOnline || d.isStale).length,
    locked: devices.filter(d => d.isLocked).length,
    needsInspection: devices.filter(d => d.needsInspection).length,
  };

  return { devices, summary, isLoading, error };
}