import React, { useEffect, useState } from 'react';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { createStackNavigator } from '@react-navigation/stack';
import type { GymDrawerParamList } from '../types/navigation';
import { DashboardScreen } from '../screens/gym/DashboardScreen';
import { DeviceDetailScreen } from '../screens/gym/DeviceDetailScreen';
import { SessionHistoryScreen } from '../screens/gym/SessionHistoryScreen';
import { DeviceHealthScreen } from '../screens/gym/DeviceHealthScreen';
import { RouteManagementScreen } from '../screens/gym/RouteManagementScreen';
import { DeviceSettingsScreen } from '../screens/gym/DeviceSettingsScreen';
import { ProvisioningScreen } from '../screens/gym/ProvisioningScreen';
import { AlertHistoryScreen } from '../screens/gym/AlertHistoryScreen';
import { useAuthStore } from '../store/authStore';
import { subscribeToUnresolvedIncidents } from '../services/firebase/incidents';

const Drawer = createDrawerNavigator<GymDrawerParamList>();
const Stack = createStackNavigator<GymDrawerParamList>();

function DashboardStack() {
  return (
    <Stack.Navigator
      screenOptions={{ headerShown: true }}
      initialRouteName="DashboardHome"
    >
      <Stack.Screen
        name="DashboardHome"
        component={DashboardScreen}
        options={{ title: 'Dashboard' }}
      />
      <Stack.Screen name="DeviceDetail" component={DeviceDetailScreen} />
      <Stack.Screen name="DeviceHealth" component={DeviceHealthScreen} />
    </Stack.Navigator>
  );
}

export function GymNavigator() {
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'demo-gym';
  const [alertBadge, setAlertBadge] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (!gymId) {
      setAlertBadge(undefined);
      return;
    }
    const unsub = subscribeToUnresolvedIncidents(
      gymId,
      (list) => {
        const count = list.filter(
          (inc) => inc.severity === 'HIGH' || inc.severity === 'CRITICAL'
        ).length;
        setAlertBadge(count || undefined);
      },
      () => {
        setAlertBadge(undefined);
      }
    );
    return unsub;
  }, [gymId]);

  return (
    <Drawer.Navigator screenOptions={{ headerShown: true }}>
      <Drawer.Screen name="Dashboard" component={DashboardStack} options={{ headerShown: false }} />
      <Drawer.Screen name="Provisioning" component={ProvisioningScreen} />
      <Drawer.Screen name="SessionHistory" component={SessionHistoryScreen} />
      <Drawer.Screen name="RouteManagement" component={RouteManagementScreen} />
      <Drawer.Screen
        name="AlertHistory"
        component={AlertHistoryScreen}
        options={{ drawerBadge: alertBadge }}
      />
      <Drawer.Screen name="Settings" component={DeviceSettingsScreen} />
    </Drawer.Navigator>
  );
}
