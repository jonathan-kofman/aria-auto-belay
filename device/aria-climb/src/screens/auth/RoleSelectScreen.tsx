import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import auth from '@react-native-firebase/auth';
import { useAuthStore } from '../../store/authStore';
import { setUserProfile, getUser } from '../../services/firebase/firestore';
import type { UserRole } from '../../types/user';

export function RoleSelectScreen() {
  const setUser = useAuthStore((s) => s.setUser);
  const setPendingRoleSelect = useAuthStore((s) => s.setPendingRoleSelect);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSelect(role: UserRole, homeGymId: string) {
    const firebaseUser = auth().currentUser;
    if (!firebaseUser) return;
    setError('');
    setLoading(true);
    try {
      await setUserProfile(firebaseUser.uid, {
        displayName: firebaseUser.displayName ?? '',
        email: firebaseUser.email ?? '',
        role,
        homeGymId: homeGymId || 'default-gym',
      });
      const user = await getUser(firebaseUser.uid);
      setUser(user ?? null);
      setPendingRoleSelect(false);
    } catch (e: any) {
      setError(e?.message ?? 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Select role</Text>
      <Text style={styles.subtitle}>After signup: gym owner / climber / guest</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <TouchableOpacity
        style={styles.button}
        onPress={() => handleSelect('owner', 'default-gym')}
        disabled={loading}
      >
        <Text style={styles.buttonText}>Gym owner</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.button}
        onPress={() => handleSelect('staff', 'default-gym')}
        disabled={loading}
      >
        <Text style={styles.buttonText}>Staff</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.button}
        onPress={() => handleSelect('climber', 'default-gym')}
        disabled={loading}
      >
        <Text style={styles.buttonText}>Climber</Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={styles.button}
        onPress={() => handleSelect('guest', '')}
        disabled={loading}
      >
        <Text style={styles.buttonText}>Guest</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 24, marginBottom: 8 },
  subtitle: { marginBottom: 24, color: '#666' },
  error: { color: 'red', marginBottom: 8 },
  button: { backgroundColor: '#1a1a2e', padding: 14, borderRadius: 8, alignItems: 'center', marginBottom: 12 },
  buttonText: { color: '#fff', fontSize: 16 },
});
