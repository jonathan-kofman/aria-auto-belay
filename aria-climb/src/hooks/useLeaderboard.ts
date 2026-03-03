import { useEffect, useState } from 'react';
import firestore from '@react-native-firebase/firestore';
import { COLLECTIONS, type UserDoc } from '../types/aria';
import { useAuthStore } from '../store/authStore';

export type LeaderboardEntry = {
  uid: string;
  displayName: string;
  bestGrade: string | null;
  totalMetersClimbed: number;
  totalFalls: number;
  totalSessions: number;
};

interface UseLeaderboardOptions {
  sortBy?: 'meters' | 'grade';
  limit?: number;
  scope?: 'gym';
}

// Simple grade ranking map (extend as needed)
const GRADE_ORDER = [
  '5.6',
  '5.7',
  '5.8',
  '5.9',
  '5.10a',
  '5.10b',
  '5.10c',
  '5.10d',
  '5.11a',
  '5.11b',
  '5.11c',
  '5.11d',
  '5.12a',
  '5.12b',
  '5.12c',
  '5.12d',
  '5.13a',
];

function gradeRank(grade: string | null | undefined): number {
  if (!grade) return -1;
  const idx = GRADE_ORDER.indexOf(grade);
  return idx === -1 ? -1 : idx;
}

export function useLeaderboard(gymIdOverride?: string, options: UseLeaderboardOptions = {}) {
  const { sortBy = 'meters', limit = 20 } = options;
  const user = useAuthStore((s) => s.user);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const gymId = gymIdOverride || user?.homeGymId;
    if (!gymId) {
      setEntries([]);
      setLoading(false);
      return;
    }

    const col = firestore().collection(COLLECTIONS.users);
    const query = col.where('gymId', '==', gymId);

    const unsub = query.onSnapshot(
      (snap) => {
        const list: LeaderboardEntry[] = [];
        snap.forEach((docSnap) => {
          const d = docSnap.data() as UserDoc;
          list.push({
            uid: d.uid,
            displayName: d.displayName,
            bestGrade: d.bestGrade ?? null,
            totalMetersClimbed: d.totalMetersClimbed ?? 0,
            totalFalls: d.totalFalls ?? 0,
            totalSessions: d.totalSessions ?? 0,
          });
        });

        list.sort((a, b) => {
          if (sortBy === 'grade') {
            return gradeRank(b.bestGrade) - gradeRank(a.bestGrade);
          }
          // default: meters
          return b.totalMetersClimbed - a.totalMetersClimbed;
        });

        setEntries(list.slice(0, limit));
        setLoading(false);
      },
      (err) => {
        setError(err as Error);
        setLoading(false);
      }
    );

    return unsub;
  }, [gymIdOverride, limit, sortBy, user?.homeGymId]);

  return { entries, loading, error };
}
