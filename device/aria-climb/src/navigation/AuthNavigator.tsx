import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import type { AuthStackParamList } from '../types/navigation';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { SignupScreen } from '../screens/auth/SignupScreen';
import { RoleSelectScreen } from '../screens/auth/RoleSelectScreen';
import { ClaimGymScreen } from '../screens/auth/ClaimGymScreen';

const Stack = createStackNavigator<AuthStackParamList>();

type Props = { initialRoute?: keyof AuthStackParamList };

export function AuthNavigator({ initialRoute = 'Login' }: Props) {
  return (
    <Stack.Navigator
      initialRouteName={initialRoute}
      screenOptions={{ headerShown: true }}
    >
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Signup" component={SignupScreen} />
      <Stack.Screen name="RoleSelect" component={RoleSelectScreen} />
      <Stack.Screen name="ClaimGym" component={ClaimGymScreen} />
    </Stack.Navigator>
  );
}
