import firestore from '@react-native-firebase/firestore';
import type { User } from '../../types/user';

const usersCol = () => firestore().collection('users');

export async function getUser(uid: string): Promise<User | null> {
  const doc = await usersCol().doc(uid).get();
  if (!doc.exists) return null;
  const d = doc.data()!;
  return {
    uid: doc.id,
    displayName: d.displayName ?? '',
    email: d.email ?? '',
    role: d.role ?? 'guest',
    homeGymId: d.homeGymId ?? '',
    certifiedLead: d.certifiedLead ?? false,
    preferences: d.preferences ?? { tensionSensitivity: 5, slackAggressiveness: 'balanced' },
    language: d.language,
    unitSystem: d.unitSystem,
  };
}

export async function setUserProfile(
  uid: string,
  data: { displayName: string; email: string; role: User['role']; homeGymId: string }
): Promise<void> {
  await usersCol().doc(uid).set(
    {
      ...data,
      certifiedLead: false,
      preferences: { tensionSensitivity: 5, slackAggressiveness: 'balanced' },
    },
    { merge: true }
  );
}
