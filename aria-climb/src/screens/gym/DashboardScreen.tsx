import React from 'react';
import { View, Text } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation } from '@react-navigation/native';

export function DashboardScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<any>();

  return (
    <View style={{ flex: 1, padding: 24 }}>
      <Text style={{ fontSize: 22 }}>{t('gym.dashboard')}</Text>
      <Text style={{ marginTop: 8, color: '#666' }}>Device grid — placeholder. TODO: Phase 2</Text>
    </View>
  );
}
