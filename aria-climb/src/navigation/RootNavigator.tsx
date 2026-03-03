import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import type { RootStackParamList } from '../types/navigation';
import { useAuthStore } from '../store/authStore';
import { AuthNavigator } from './AuthNavigator';
import { GymNavigator } from './GymNavigator';
import { ClimberNavigator } from './ClimberNavigator';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';

const Stack = createStackNavigator<RootStackParamList>();

export function RootNavigator() {
  const { user, isLoading, pendingRoleSelect } = useAuthStore();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (pendingRoleSelect) {
    return <AuthNavigator initialRoute="RoleSelect" />;
  }

  if (!user) {
    return <AuthNavigator initialRoute="Login" />;
  }

  // Owner or staff accounts without a gymId should complete gym onboarding first.
  if ((user.role === 'owner' || user.role === 'staff') && !user.homeGymId) {
    return <AuthNavigator initialRoute="ClaimGym" />;
  }

  if (useAuthStore.getState().isGymMode) {
    return <GymNavigator />;
  }

  return <ClimberNavigator />;
}
