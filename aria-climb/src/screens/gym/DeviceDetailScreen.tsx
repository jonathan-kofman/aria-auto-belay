import React from 'react';
import { View, Text } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import type { GymDrawerParamList } from '../../types/navigation';

export function DeviceDetailScreen() {
  const route = useRoute<RouteProp<GymDrawerParamList, 'DeviceDetail'>>();
  const { deviceId } = route.params;

  return (
    <View style={{ flex: 1, padding: 24 }}>
      <Text style={{ fontSize: 22 }}>Device detail</Text>
      <Text style={{ marginTop: 8, color: '#666' }}>deviceId: {deviceId}</Text>
    </View>
  );
}
