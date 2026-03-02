import React from 'react';
import { View, Text } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import type { ClimberStackParamList } from '../../types/navigation';

export function SessionDetailScreen() {
  const route = useRoute<RouteProp<ClimberStackParamList, 'SessionDetail'>>();
  const { sessionId } = route.params;

  return (
    <View style={{ flex: 1, padding: 24 }}>
      <Text style={{ fontSize: 22 }}>Session detail</Text>
      <Text style={{ marginTop: 8, color: '#666' }}>sessionId: {sessionId}</Text>
    </View>
  );
}
