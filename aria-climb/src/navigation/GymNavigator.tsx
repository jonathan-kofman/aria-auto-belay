import React from 'react';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { createStackNavigator } from '@react-navigation/stack';
import type { GymDrawerParamList } from '../types/navigation';
import { DashboardScreen } from '../screens/gym/DashboardScreen';
import { DeviceDetailScreen } from '../screens/gym/DeviceDetailScreen';
import { SessionHistoryScreen } from '../screens/gym/SessionHistoryScreen';
import { RouteManagementScreen } from '../screens/gym/RouteManagementScreen';
import { DeviceSettingsScreen } from '../screens/gym/DeviceSettingsScreen';
import { AlertHistoryScreen } from '../screens/gym/AlertHistoryScreen';

const Drawer = createDrawerNavigator<GymDrawerParamList>();
const Stack = createStackNavigator<GymDrawerParamList>();

function DashboardStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: true }}>
      <Stack.Screen name="Dashboard" component={DashboardScreen} />
      <Stack.Screen name="DeviceDetail" component={DeviceDetailScreen} />
    </Stack.Navigator>
  );
}

export function GymNavigator() {
  return (
    <Drawer.Navigator screenOptions={{ headerShown: true }}>
      <Drawer.Screen name="Dashboard" component={DashboardStack} options={{ headerShown: false }} />
      <Drawer.Screen name="SessionHistory" component={SessionHistoryScreen} />
      <Drawer.Screen name="RouteManagement" component={RouteManagementScreen} />
      <Drawer.Screen name="AlertHistory" component={AlertHistoryScreen} />
      <Drawer.Screen name="Settings" component={DeviceSettingsScreen} />
    </Drawer.Navigator>
  );
}
