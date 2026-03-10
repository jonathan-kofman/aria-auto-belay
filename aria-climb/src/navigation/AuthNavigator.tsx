import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import type { AuthStackParamList } from '../types/navigation';
import { LoginScreen } from '../screens/auth/LoginScreen';
import { SignupScreen } from '../screens/auth/SignupScreen';
import { RoleSelectScreen } from '../screens/auth/RoleSelectScreen';
import { ClaimGymScreen } from '../screens/auth/ClaimGymScreen';

const Stack = createStackNavigator<AuthStackParamList>();

const headerStyle = {
  headerStyle: { backgroundColor: '#1a1a2e' },
  headerTintColor: '#fff',
  headerTitleStyle: { fontWeight: '600', fontSize: 17 },
};

type Props = { initialRoute?: keyof AuthStackParamList };

export function AuthNavigator({ initialRoute = 'Login' }: Props) {
  return (
    <Stack.Navigator
      initialRouteName={initialRoute}
      screenOptions={{ headerShown: true, ...headerStyle }}
    >
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Signup" component={SignupScreen} />
      <Stack.Screen name="RoleSelect" component={RoleSelectScreen} />
      <Stack.Screen name="ClaimGym" component={ClaimGymScreen} />
    </Stack.Navigator>
  );
}
