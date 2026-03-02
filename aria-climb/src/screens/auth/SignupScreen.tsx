import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';
import * as authService from '../../services/firebase/auth';

export function SignupScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<any>();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');

  async function handleSignup() {
    setError('');
    if (!email.trim() || !password || !displayName.trim()) {
      setError(t('common.error'));
      return;
    }
    try {
      await authService.signUp(email.trim(), password, displayName.trim());
      navigation.replace('RoleSelect');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('common.error'));
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('auth.signup')}</Text>
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
      <TextInput
        style={styles.input}
        placeholder="Display name"
        value={displayName}
        onChangeText={setDisplayName}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <TouchableOpacity style={styles.button} onPress={handleSignup}>
        <Text style={styles.buttonText}>{t('auth.signup')}</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 24, marginBottom: 16 },
  input: { borderWidth: 1, padding: 12, marginBottom: 12, borderRadius: 8 },
  error: { color: 'red', marginBottom: 8 },
  button: { backgroundColor: '#1a1a2e', padding: 14, borderRadius: 8, alignItems: 'center', marginTop: 8 },
  buttonText: { color: '#fff', fontSize: 16 },
});
