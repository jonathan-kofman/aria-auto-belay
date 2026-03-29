import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../store/authStore';
import { claimGym, joinGymAsStaff } from '../../services/firebase/gymClaim';

export function ClaimGymScreen() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);

  const [code, setCode] = useState('');
  const [gymId, setGymId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!user) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>{t('auth.login')}</Text>
        <Text style={styles.subtitle}>Please log in again to claim a gym.</Text>
      </View>
    );
  }

  const isOwner = user.role === 'owner';
  const isStaff = user.role === 'staff';

  async function handleOwnerClaim() {
    setError('');
    const trimmed = code.trim();
    if (!trimmed) {
      setError('Enter a claim code.');
      return;
    }
    setLoading(true);
    try {
      const result = await claimGym(trimmed);
      if (!result.success) {
        if (result.error === 'INVALID_CODE') setError('Code not found.');
        else if (result.error === 'ALREADY_CLAIMED') setError('This code has already been used.');
        else if (result.error === 'EXPIRED') setError('This code has expired.');
        else setError('Unable to claim gym right now.');
        return;
      }
      if (result.gymId) {
        setUser({ ...user, homeGymId: result.gymId, role: 'owner' });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  async function handleStaffJoin() {
    setError('');
    const trimmed = gymId.trim();
    if (!trimmed) {
      setError('Enter a gym ID.');
      return;
    }
    setLoading(true);
    try {
      const ok = await joinGymAsStaff(trimmed);
      if (!ok) {
        setError('Gym not found or join failed.');
        return;
      }
      setUser({ ...user, homeGymId: trimmed, role: 'staff' });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Connect to your gym</Text>
      <Text style={styles.subtitle}>
        {isOwner
          ? 'Enter the claim code you received for your gym.'
          : isStaff
          ? 'Enter the gym ID provided by your owner/manager.'
          : 'Your account is not marked as owner or staff; gym claim is optional.'}
      </Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {isOwner && (
        <>
          <TextInput
            style={styles.input}
            placeholder="Claim code (e.g. ARIA-001)"
            value={code}
            onChangeText={setCode}
            autoCapitalize="characters"
          />
          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleOwnerClaim}
            disabled={loading}
          >
            <Text style={styles.buttonText}>{loading ? 'Claiming…' : 'Claim gym as owner'}</Text>
          </TouchableOpacity>
        </>
      )}

      {isStaff && (
        <>
          <TextInput
            style={styles.input}
            placeholder="Gym ID (e.g. gym_001)"
            value={gymId}
            onChangeText={setGymId}
            autoCapitalize="none"
          />
          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleStaffJoin}
            disabled={loading}
          >
            <Text style={styles.buttonText}>{loading ? 'Joining…' : 'Join gym as staff'}</Text>
          </TouchableOpacity>
        </>
      )}

      {!isOwner && !isStaff && (
        <Text style={styles.subtitle}>
          You can continue as a climber/guest without claiming a gym.
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center' },
  title: { fontSize: 24, marginBottom: 8 },
  subtitle: { marginBottom: 16, color: '#666' },
  input: { borderWidth: 1, padding: 12, marginBottom: 12, borderRadius: 8 },
  error: { color: 'red', marginBottom: 8 },
  button: {
    backgroundColor: '#1a1a2e',
    padding: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: { color: '#fff', fontSize: 16 },
});

