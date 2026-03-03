import { useEffect, useState } from 'react';
import { ARIADeviceState } from '../types/aria';
import { subscribeToDevice } from '../services/firebase/ariaDevice';

interface UseARIADeviceResult {
  device: ARIADeviceState | null;
  isLoading: boolean;
  error: Error | null;
}

export function useARIADevice(gymId: string, deviceId: string): UseARIADeviceResult {
  const [device, setDevice] = useState<ARIADeviceState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!gymId || !deviceId) return;

    const unsub = subscribeToDevice(
      gymId,
      deviceId,
      (dev) => {
        setDevice(dev);
        setIsLoading(false);
      },
      (err) => {
        setError(err);
        setIsLoading(false);
      }
    );

    return unsub;
  }, [gymId, deviceId]);

  return { device, isLoading, error };
}