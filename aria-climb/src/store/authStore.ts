import { create } from 'zustand';
import type { User } from '../types/user';
import * as authService from '../services/firebase/auth';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  pendingRoleSelect: boolean;
  isGymMode: boolean;
  setUser: (user: User | null) => void;
  setPendingRoleSelect: (value: boolean) => void;
  setLoading: (value: boolean) => void;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  pendingRoleSelect: false,
  isGymMode: false,

  setUser: (user) =>
    set({
      user,
      isGymMode: user ? (user.role === 'owner' || user.role === 'staff') : false,
    }),

  setPendingRoleSelect: (pendingRoleSelect) => set({ pendingRoleSelect }),

  setLoading: (isLoading) => set({ isLoading }),

  signOut: async () => {
    await authService.signOut();
    set({ user: null, pendingRoleSelect: false, isGymMode: false });
  },
}));
