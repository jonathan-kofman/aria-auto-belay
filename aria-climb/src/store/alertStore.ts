// TODO: Phase 4
import { create } from 'zustand';
import type { Alert } from '../types/alert';

interface AlertState {
  activeAlerts: Alert[];
  addAlert: (alert: Alert) => void;
  dismissAlert: (alertId: string) => void;
  clearAlert: (alertId: string) => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  activeAlerts: [],
  addAlert: (alert) =>
    set((s) => ({ activeAlerts: [...s.activeAlerts, alert] })),
  dismissAlert: (alertId) =>
    set((s) => ({
      activeAlerts: s.activeAlerts.filter((a) => a.id !== alertId),
    })),
  clearAlert: (alertId) =>
    set((s) => ({
      activeAlerts: s.activeAlerts.filter((a) => a.id !== alertId),
    })),
}));
