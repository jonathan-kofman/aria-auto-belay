import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';
import type { User } from '../../types/user';

export function LoginScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<any>();
  const setUser = useAuthStore((s) => s.setUser);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [roleOverride, setRoleOverride] = useState<'climber' | 'owner'>('climber');
  const [error] = useState('');

  function handleLogin() {
    const trimmedEmail = email.trim();
    const role: User['role'] = __DEV__ ? roleOverride : 'climber';

    const demoUser: User = {
      uid: 'demo',
      displayName: trimmedEmail || (role === 'owner' ? 'Gym manager' : 'Demo climber'),
      email: trimmedEmail || (role === 'owner' ? 'gym@example.com' : 'demo@example.com'),
      role,
      homeGymId: 'demo-gym',
      certifiedLead: false,
      preferences: {
        tensionSensitivity: 5,
        slackAggressiveness: 'balanced',
      },
    };
    setUser(demoUser);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('auth.login')}</Text>
      {__DEV__ && (
        <View style={styles.devRoleBlock}>
          <Text style={styles.devLabel}>Dev role override</Text>
          <View style={styles.devChipRow}>
            <TouchableOpacity
              style={[
                styles.devChip,
                roleOverride === 'climber' && styles.devChipActive,
              ]}
              onPress={() => setRoleOverride('climber')}
            >
              <Text
                style={
                  roleOverride === 'climber'
                    ? styles.devChipTextActive
                    : styles.devChipText
                }
              >
                Climber
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[
                styles.devChip,
                roleOverride === 'owner' && styles.devChipActive,
              ]}
              onPress={() => setRoleOverride('owner')}
            >
              <Text
                style={
                  roleOverride === 'owner'
                    ? styles.devChipTextActive
                    : styles.devChipText
                }
              >
                Gym manager
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
      <TextInput
        style={styles.input}
        placeholder={t('auth.email')}
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        keyboardType="email-address"
      />
      <TextInput
        style={styles.input}
        placeholder={t('auth.password')}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <TouchableOpacity style={styles.button} onPress={handleLogin}>
        <Text style={styles.buttonText}>{t('auth.login')}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.navigate('Signup')}>
        <Text style={styles.link}>{t('auth.signup')}</Text>
      </TouchableOpacity>
      <TouchableOpacity onPress={() => navigation.navigate('RoleSelect')} style={styles.linkButton}>
        <Text style={styles.link}>Use app without signing in (select role)</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 24, marginBottom: 16 },
  devRoleBlock: { marginBottom: 12 },
  devLabel: { fontSize: 12, color: '#888', marginBottom: 4 },
  devChipRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
  },
  devChip: {
    borderWidth: 1,
    borderRadius: 999,
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderColor: '#ccc',
    marginRight: 8,
  },
  devChipActive: {
    backgroundColor: '#1a1a2e',
    borderColor: '#1a1a2e',
  },
  devChipText: { color: '#333', fontSize: 12 },
  devChipTextActive: { color: '#fff', fontSize: 12, fontWeight: '600' },
  input: { borderWidth: 1, padding: 12, marginBottom: 12, borderRadius: 8 },
  error: { color: 'red', marginBottom: 8 },
  button: { backgroundColor: '#1a1a2e', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  buttonText: { color: '#fff', fontSize: 16 },
  link: { marginTop: 16, textAlign: 'center', color: '#666' },
  linkButton: { marginTop: 8 },
});
