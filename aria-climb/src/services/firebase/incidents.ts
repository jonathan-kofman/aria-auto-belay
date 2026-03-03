import firestore from '@react-native-firebase/firestore';
import { IncidentDoc, Incident, IncidentSeverity, COLLECTIONS } from '../../types/aria';

function parseIncident(doc: IncidentDoc): Incident {
  return {
    ...doc,
    timestamp: doc.timestamp.toDate(),
    resolvedAt: doc.resolvedAt?.toDate() ?? null,
  };
}

export function subscribeToIncidents(
  gymId: string,
  onUpdate: (incidents: Incident[]) => void,
  onError: (err: Error) => void,
  limitTo = 50
): () => void {
  return firestore()
    .collection(COLLECTIONS.incidents(gymId))
    .orderBy('timestamp', 'desc')
    .limit(limitTo)
    .onSnapshot(
      snap => onUpdate(snap.docs.map(d => parseIncident(d.data() as IncidentDoc))),
      onError
    );
}

export function subscribeToUnresolvedIncidents(
  gymId: string,
  onUpdate: (incidents: Incident[]) => void,
  onError: (err: Error) => void
): () => void {
  return firestore()
    .collection(COLLECTIONS.incidents(gymId))
    .where('resolved', '==', false)
    .orderBy('timestamp', 'desc')
    .onSnapshot(
      snap => onUpdate(snap.docs.map(d => parseIncident(d.data() as IncidentDoc))),
      onError
    );
}

export async function resolveIncident(
  gymId: string,
  incidentId: string,
  resolvedBy: string,
  notes: string
): Promise<void> {
  await firestore()
    .collection(COLLECTIONS.incidents(gymId))
    .doc(incidentId)
    .update({
      resolved: true,
      resolvedBy,
      resolvedAt: firestore.Timestamp.now(),
      resolutionNotes: notes,
    });
}

export async function createIncident(
  incident: Omit<IncidentDoc, 'incidentId'>
): Promise<string> {
  const ref = firestore()
    .collection(COLLECTIONS.incidents(incident.gymId))
    .doc();
  await ref.set({ ...incident, incidentId: ref.id });
  return ref.id;
}