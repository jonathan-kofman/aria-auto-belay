import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';

export function ProfileScreen() {
  const { t } = useTranslation();
  const { user, signOut } = useAuthStore();

  return (
    <View style={{ flex: 1, padding: 24 }}>
      <Text style={{ fontSize: 22 }}>{t('climber.profile')}</Text>
      {user ? (
        <Text style={{ marginTop: 8 }}>{user.displayName || user.email}</Text>
      ) : null}
      <TouchableOpacity
        onPress={() => signOut()}
        style={{ marginTop: 24, padding: 12, backgroundColor: '#ccc', borderRadius: 8 }}
      >
        <Text>{t('auth.logout')}</Text>
      </TouchableOpacity>
    </View>
  );
}
