import auth from '@react-native-firebase/auth';
import type { User } from '../../types/user';
import { getUser, setUserProfile } from './firestore';

export async function signIn(email: string, password: string): Promise<User | null> {
  const cred = await auth().signInWithEmailAndPassword(email, password);
  const uid = cred.user.uid;
  const profile = await getUser(uid);
  return profile;
}

export async function signUp(
  email: string,
  password: string,
  displayName: string
): Promise<string> {
  const cred = await auth().createUserWithEmailAndPassword(email, password);
  await cred.user.updateProfile({ displayName });
  // Default all new signups to climber; management roles should be assigned via claims/admin.
  await setUserProfile(cred.user.uid, {
    displayName,
    email,
    role: 'climber',
    homeGymId: 'default-gym',
  });
  return cred.user.uid;
}

export function signOut(): Promise<void> {
  return auth().signOut();
}

export type AuthStateResult = { user: User | null; pendingRoleSelect: boolean };

export function onAuthStateChanged(
  callback: (result: AuthStateResult) => void
): () => void {
  return auth().onAuthStateChanged(async (firebaseUser) => {
    if (!firebaseUser) {
      callback({ user: null, pendingRoleSelect: false });
      return;
    }
    const profile = await getUser(firebaseUser.uid);
    if (profile) {
      callback({ user: profile, pendingRoleSelect: false });
    } else {
      callback({ user: null, pendingRoleSelect: true });
    }
  });
}
