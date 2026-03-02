import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import type { ClimberTabParamList, ClimberStackParamList } from '../types/navigation';
import { HomeScreen } from '../screens/climber/HomeScreen';
import { SessionsScreen } from '../screens/climber/SessionsScreen';
import { SessionDetailScreen } from '../screens/climber/SessionDetailScreen';
import { LeaderboardScreen } from '../screens/climber/LeaderboardScreen';
import { ProfileScreen } from '../screens/climber/ProfileScreen';

const Tab = createBottomTabNavigator<ClimberTabParamList>();
const Stack = createStackNavigator<ClimberStackParamList>();

function SessionsStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: true }}>
      <Stack.Screen name="SessionList" component={SessionsScreen} />
      <Stack.Screen name="SessionDetail" component={SessionDetailScreen} />
    </Stack.Navigator>
  );
}

export function ClimberNavigator() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: true }}>
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Sessions" component={SessionsStack} />
      <Tab.Screen name="Leaderboard" component={LeaderboardScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}
