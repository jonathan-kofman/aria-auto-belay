import React from 'react';
import { View, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

export function RouteManagementScreen() {
  const { t } = useTranslation();
  return (
    <View style={{ flex: 1, padding: 24 }}>
      <Text style={{ fontSize: 22 }}>{t('gym.routes')}</Text>
      <Text style={{ marginTop: 8, color: '#666' }}>Placeholder</Text>
    </View>
  );
}
