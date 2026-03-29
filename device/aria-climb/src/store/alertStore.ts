import { create } from 'zustand';
import type { Alert } from '../types/alert';

interface AlertState {
  alerts: Alert[];
  unreadCount: number;
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  markRead: () => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  unreadCount: 0,

  setAlerts: (alerts) =>
    set((s) => {
      const newCount = alerts.filter((a) => !s.alerts.some((e) => e.id === a.id)).length;
      return { alerts, unreadCount: s.unreadCount + newCount };
    }),

  addAlert: (alert) =>
    set((s) => ({ alerts: [alert, ...s.alerts], unreadCount: s.unreadCount + 1 })),

  markRead: () => set({ unreadCount: 0 }),

  clearAlerts: () => set({ alerts: [], unreadCount: 0 }),
}));
