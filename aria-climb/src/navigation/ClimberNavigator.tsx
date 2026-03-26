import React from 'react';
import { View, TouchableOpacity, Text } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { createDrawerNavigator } from '@react-navigation/drawer';
import { createStackNavigator } from '@react-navigation/stack';
import type { ClimberDrawerParamList, ClimberStackParamList } from '../types/navigation';
import { HomeScreen } from '../screens/climber/HomeScreen';
import { SessionsScreen } from '../screens/climber/SessionsScreen';
import { SessionDetailScreen } from '../screens/climber/SessionDetailScreen';
import { LeaderboardScreen } from '../screens/climber/LeaderboardScreen';
import { ProfileScreen } from '../screens/climber/ProfileScreen';
import { GymOnboardingScreen } from '../screens/climber/GymOnboardingScreen';
import { LiveSessionScreen } from '../screens/climber/LiveSessionScreen';
import { useAuthStore } from '../store/authStore';

const Drawer = createDrawerNavigator<ClimberDrawerParamList>();
const Stack = createStackNavigator<ClimberStackParamList>();

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
  const openDrawer = () => {
    let nav: any = navigation;
    while (nav?.getParent?.()) {
      nav = nav.getParent();
    }
    nav?.openDrawer?.();
  };
  return (
    <TouchableOpacity
      onPress={openDrawer}
      style={{ marginRight: 12, padding: 8 }}
      accessibilityLabel="Open menu"
    >
      <Text style={{ color: '#fff', fontSize: 22, fontWeight: '700' }}>≡</Text>
    </TouchableOpacity>
  );
}

function SessionsStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: true,
        ...headerStyle,
        headerRight: () => <DrawerMenuButton />,
      }}
    >
      <Stack.Screen name="SessionList" component={SessionsScreen} />
      <Stack.Screen name="SessionDetail" component={SessionDetailScreen} />
    </Stack.Navigator>
  );
}

export function ClimberNavigator() {
  return (
    <View style={{ flex: 1 }}>
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
        <Drawer.Screen
          name="Home"
          component={HomeScreen}
          options={{
            title: 'Home',
            headerLeft: () => <BackToRoleSelectButton />,
            headerRight: () => <DrawerMenuButton />,
          }}
        />
        <Drawer.Screen name="Sessions" component={SessionsStack} options={{ title: 'Sessions' }} />
        <Drawer.Screen name="Leaderboard" component={LeaderboardScreen} options={{ title: 'Leaderboard' }} />
        <Drawer.Screen name="Profile" component={ProfileScreen} options={{ title: 'Profile' }} />
        <Drawer.Screen
          name="PairDevice"
          component={GymOnboardingScreen}
          options={{ title: 'Pair with ARIA' }}
        />
        <Drawer.Screen
          name="LiveSession"
          component={LiveSessionScreen}
          options={{ title: 'Live Session', drawerItemStyle: { display: 'none' } }}
        />
      </Drawer.Navigator>
    </View>
  );
}
