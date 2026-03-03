export type ARIAState =
  | 'IDLE' | 'CLIMBING' | 'CLIPPING' | 'TAKE'
  | 'REST' | 'LOWER' | 'WATCH_ME' | 'UP'
  | 'FAULT' | 'LOCKOUT' | 'MAINTENANCE';

export type VoiceCommand = 'take' | 'slack' | 'lower' | 'up' | 'watch_me' | 'rest' | 'climbing';

export type EventType =
  | 'FALL_CAUGHT' | 'VOICE_CMD' | 'CLIP_DETECTED' | 'STATE_CHANGE'
  | 'FAULT' | 'MOTOR_FAULT' | 'TENSION_SPIKE' | 'HEARTBEAT_LOST'
  | 'MAINTENANCE_START' | 'MAINTENANCE_END';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type MaintenanceAction =
  | 'PAUSE_MOTOR' | 'RESUME_MOTOR' | 'LOCKOUT' | 'RETURN_TO_SERVICE'
  | 'FIRMWARE_UPDATE' | 'CALIBRATION' | 'INSPECTION';

export type UserRole = 'climber' | 'staff' | 'owner' | 'technician';

// Firestore document timestamp wrapper
export interface FirebaseTimestamp {
  seconds: number;
  nanoseconds: number;
  toDate(): Date;
}

// ─── Firestore Document Types ────────────────────────────────────────────────

export interface ARIADeviceDoc {
  deviceId: string;
  gymId: string;
  state: ARIAState;
  tension: number;
  motorPosition: number;
  ropeOut: number;
  isOnline: boolean;
  lastHeartbeat: FirebaseTimestamp;
  firmwareVersion: string;
  uptimeSeconds: number;
  motorHours: number;
  totalFallsCaught: number;
  cycleCount: number;
  wallId: string;
  wallName: string;
  gradeBand: string;
  installDate: FirebaseTimestamp;
  nextInspectionDue: FirebaseTimestamp;
  isLocked: boolean;
  isInMaintenance: boolean;
  lastMaintenanceAt: FirebaseTimestamp | null;
}

export interface ARIAEventDoc {
  eventId: string;
  deviceId: string;
  gymId: string;
  sessionId: string | null;
  type: EventType;
  timestamp: FirebaseTimestamp;
  payload: Record<string, unknown>;
}

export interface TensionSample {
  t: number;
  tension: number;
  state: ARIAState;
}

export interface SessionDoc {
  sessionId: string;
  gymId: string;
  deviceId: string;
  climberId: string;
  climberDisplayName: string;
  routeId: string | null;
  routeName: string | null;
  wallId: string;
  startTime: FirebaseTimestamp;
  endTime: FirebaseTimestamp | null;
  durationSeconds: number | null;
  fallCount: number;
  maxHeightMeters: number;
  clipCount: number;
  voiceCommandCount: number;
  tensionProfile: TensionSample[];
  isActive: boolean;
}

export interface IncidentDoc {
  incidentId: string;
  gymId: string;
  deviceId: string;
  sessionId: string | null;
  type: EventType;
  severity: IncidentSeverity;
  timestamp: FirebaseTimestamp;
  description: string;
  resolved: boolean;
  resolvedBy: string | null;
  resolvedAt: FirebaseTimestamp | null;
  resolutionNotes: string | null;
  triggeringEventId: string | null;
}

export interface MaintenanceLogDoc {
  logId: string;
  gymId: string;
  deviceId: string;
  action: MaintenanceAction;
  performedBy: string;
  performedByName: string;
  timestamp: FirebaseTimestamp;
  notes: string;
  firmwareVersionBefore: string | null;
  firmwareVersionAfter: string | null;
}

export interface CommandDoc {
  commandId: string;
  deviceId: string;
  gymId: string;
  command: MaintenanceAction | 'SET_STATE' | 'REBOOT' | 'CALIBRATE_ENCODER';
  params: Record<string, unknown>;
  issuedBy: string;
  issuedByName: string;
  issuedAt: FirebaseTimestamp;
  acknowledged: boolean;
  acknowledgedAt: FirebaseTimestamp | null;
  result: 'PENDING' | 'SUCCESS' | 'FAILED' | null;
  errorMessage: string | null;
}

export interface UserDoc {
  uid: string;
  displayName: string;
  email: string;
  role: UserRole;
  gymId: string;
  totalSessions: number;
  totalFalls: number;
  bestGrade: string | null;
  totalMetersClimbed: number;
}

// ─── Parsed (Date-converted) Types ───────────────────────────────────────────

export interface ARIADeviceState extends Omit<
  ARIADeviceDoc,
  'lastHeartbeat' | 'installDate' | 'nextInspectionDue' | 'lastMaintenanceAt'
> {
  lastHeartbeat: Date;
  installDate: Date;
  nextInspectionDue: Date;
  lastMaintenanceAt: Date | null;
  isStale: boolean;
  needsInspection: boolean;
}

export interface Session extends Omit<SessionDoc, 'startTime' | 'endTime'> {
  startTime: Date;
  endTime: Date | null;
}

export interface Incident extends Omit<IncidentDoc, 'timestamp' | 'resolvedAt'> {
  timestamp: Date;
  resolvedAt: Date | null;
}

// ─── Collection Paths ────────────────────────────────────────────────────────

export const COLLECTIONS = {
  gyms: 'gyms',
  users: 'users',
  commands: 'commands',
  devices: (gymId: string) => `gyms/${gymId}/devices`,
  device: (gymId: string, deviceId: string) => `gyms/${gymId}/devices/${deviceId}`,
  events: (gymId: string, deviceId: string) => `gyms/${gymId}/devices/${deviceId}/events`,
  sessions: (gymId: string) => `gyms/${gymId}/sessions`,
  incidents: (gymId: string) => `gyms/${gymId}/incidents`,
  maintenanceLogs: (gymId: string) => `gyms/${gymId}/maintenanceLog`,
  command: (deviceId: string) => `commands/${deviceId}`,
} as const;

