// Firestore query hook for session list
export function useSessionHistory(_gymId?: string, _deviceId?: string) {
  return { sessions: [], loading: false };
}
