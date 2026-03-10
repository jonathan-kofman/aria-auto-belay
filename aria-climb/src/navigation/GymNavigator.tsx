import React, { useEffect, useState } from 'react';
import { View, TouchableOpacity, Text } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { createStackNavigator } from '@react-navigation/stack';
import type { GymDrawerParamList } from '../types/navigation';
import { AlertBanner } from '../components/shared/AlertBanner';
import { DashboardScreen } from '../screens/gym/DashboardScreen';
import { DeviceDetailScreen } from '../screens/gym/DeviceDetailScreen';
import { SessionHistoryScreen } from '../screens/gym/SessionHistoryScreen';
import { DeviceHealthScreen } from '../screens/gym/DeviceHealthScreen';
import { RouteManagementScreen } from '../screens/gym/RouteManagementScreen';
import { DeviceSettingsScreen } from '../screens/gym/DeviceSettingsScreen';
import { ProvisioningScreen } from '../screens/gym/ProvisioningScreen';
import { AlertHistoryScreen } from '../screens/gym/AlertHistoryScreen';
import { SafetyCameraTestScreen } from '../screens/gym/SafetyCameraTestScreen';
import { useAuthStore } from '../store/authStore';
import { subscribeToUnresolvedIncidents } from '../services/firebase/incidents';

const Drawer = createDrawerNavigator<GymDrawerParamList>();
const Stack = createStackNavigator<GymDrawerParamList>();

const headerStyle = {
  headerStyle: { backgroundColor: '#1a1a2e' },
  headerTintColor: '#fff',
  headerTitleStyle: { fontWeight: '600', fontSize: 17 },
};

function BackToRoleSelectButton() {
  const setPendingRoleSelect = useAuthStore((s) => s.setPendingRoleSelect);
  return (
    <TouchableOpacity
      onPress={() => setPendingRoleSelect(true)}
      style={{ marginLeft: 8, padding: 8 }}
      accessibilityLabel="Back to select role"
    >
      <Text style={{ color: '#fff', fontSize: 24 }}>←</Text>
    </TouchableOpacity>
  );
}

function DrawerMenuButton() {
  const navigation = useNavigation();
  const parent = navigation.getParent?.();
  const openDrawer = (parent as any)?.openDrawer;
  return (
    <TouchableOpacity
      onPress={() => typeof openDrawer === 'function' && openDrawer()}
      style={{ marginRight: 12, padding: 8 }}
      accessibilityLabel="Open menu"
    >
      <Text style={{ color: '#fff', fontSize: 22, fontWeight: '700' }}>≡</Text>
    </TouchableOpacity>
  );
}

function DashboardStack() {
  return (
    <Stack.Navigator
      screenOptions={{ headerShown: true, ...headerStyle }}
      initialRouteName="DashboardHome"
    >
      <Stack.Screen
        name="DashboardHome"
        component={DashboardScreen}
        options={{
          title: 'Dashboard',
          headerLeft: () => <BackToRoleSelectButton />,
          headerRight: () => <DrawerMenuButton />,
        }}
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
    <View style={{ flex: 1 }}>
      <AlertBanner />
      <Drawer.Navigator
        screenOptions={{
          headerShown: true,
          ...headerStyle,
          drawerStyle: { backgroundColor: '#1a1a2e' },
          drawerActiveTintColor: '#fff',
          drawerInactiveTintColor: 'rgba(255,255,255,0.7)',
          drawerActiveBackgroundColor: 'rgba(255,255,255,0.15)',
        }}
      >
        <Drawer.Screen name="Dashboard" component={DashboardStack} options={{ headerShown: false, title: 'Dashboard' }} />
        <Drawer.Screen name="Provisioning" component={ProvisioningScreen} options={{ title: 'Provisioning' }} />
        <Drawer.Screen
          name="SafetyCameraTest"
          component={SafetyCameraTestScreen}
          options={{ title: 'Safety / Camera test' }}
        />
        <Drawer.Screen name="SessionHistory" component={SessionHistoryScreen} options={{ title: 'Session history' }} />
        <Drawer.Screen name="RouteManagement" component={RouteManagementScreen} options={{ title: 'Route management' }} />
        <Drawer.Screen
          name="AlertHistory"
          component={AlertHistoryScreen}
          options={{ title: 'Alert history', drawerBadge: alertBadge }}
        />
        <Drawer.Screen name="Settings" component={DeviceSettingsScreen} options={{ title: 'Settings' }} />
      </Drawer.Navigator>
    </View>
  );
}
