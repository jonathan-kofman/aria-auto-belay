import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';
// Minimal gym/user shapes for claim flows; extend as needed.
export interface GymDoc {
  id?: string;
  name?: string;
}
export interface UserDoc {
  uid: string;
}

export interface ClaimResult {
  success: boolean;
  gym?: GymDoc;
  gymId?: string;
  error?: 'INVALID_CODE' | 'ALREADY_CLAIMED' | 'EXPIRED' | 'UNKNOWN';
}

/**
 * Gym claim codes live at /gymClaims/{code}
 * Structure: { gymId, expiresAt, claimedBy: null }
 * Created manually by you (or later an admin panel) when onboarding a gym
 */
export async function claimGym(code: string): Promise<ClaimResult> {
  const uid = auth().currentUser?.uid;
  if (!uid) throw new Error('Not authenticated');

  const claimRef = firestore().collection('gymClaims').doc(code.toUpperCase().trim());

  try {
    return await firestore().runTransaction(async tx => {
      const claimSnap = await tx.get(claimRef);

      if (!claimSnap.exists) {
        return { success: false, error: 'INVALID_CODE' as const };
      }

      const claim = claimSnap.data()!;

      if (claim.claimedBy !== null) {
        return { success: false, error: 'ALREADY_CLAIMED' as const };
      }

      if (claim.expiresAt.toDate() < new Date()) {
        return { success: false, error: 'EXPIRED' as const };
      }

      // Mark claim as used
      tx.update(claimRef, { claimedBy: uid, claimedAt: firestore.Timestamp.now() });

      // Update user doc with gymId and owner role
      tx.update(firestore().collection('users').doc(uid), {
        gymId: claim.gymId,
        role: 'owner',
      });

      // Fetch gym doc to return
      const gymSnap = await firestore().collection('gyms').doc(claim.gymId).get();
      return { success: true, gym: gymSnap.data() as GymDoc, gymId: claim.gymId as string };
    });
  } catch (e) {
    return { success: false, error: 'UNKNOWN' };
  }
}

/** Staff join a gym (simpler — just needs gymId, role assigned by owner later) */
export async function joinGymAsStaff(gymId: string): Promise<boolean> {
  const uid = auth().currentUser?.uid;
  if (!uid) return false;

  const gymSnap = await firestore().collection('gyms').doc(gymId).get();
  if (!gymSnap.exists) return false;

  await firestore().collection('users').doc(uid).update({
    gymId,
    role: 'staff',
  });

  return true;
}

// Firestore — seed a claim code manually in the console:
// /gymClaims/ARIA-001
//   gymId: "gym_001"
//   expiresAt: <30 days from now>
//   claimedBy: null
//   claimedAt: null
//
// That's the code an owner enters in the app. You generate these when onboarding a gym — later you can automate it.
//
// Suggested Firestore rule:
// match /gymClaims/{code} {
//   allow read: if request.auth != null;
//   allow write: if false; // only via transaction from client, handled above
// }