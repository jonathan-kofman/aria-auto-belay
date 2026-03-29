/**
 * ARIA device state machine states — mirrors firmware/stm32/aria_main.cpp ARIAState enum.
 * Byte values: IDLE=0, CLIMBING=1, CLIPPING=2, TAKE=3, REST=4,
 *              LOWER=5, WATCH_ME=6, UP=7, ESTOP=8
 */
export type ARIAState =
  | 'IDLE'
  | 'CLIMBING'
  | 'CLIPPING'
  | 'TAKE'
  | 'REST'
  | 'LOWER'
  | 'WATCH_ME'
  | 'UP'
  | 'ESTOP'
  | 'UNKNOWN';

export interface ARIATelemetry {
  /** Raw load-cell tension in Newtons */
  tension_N: number;
  /** Current state machine state */
  state: ARIAState;
  /** Rope speed in m/s (positive = paying out, negative = taking) */
  rope_speed_ms: number;
  /** Motor current in Amps */
  motor_current_A: number;
  /** Battery voltage */
  battery_V: number;
  /** Timestamp (ms since epoch) */
  ts: number;
}

export interface ARIADevice {
  id: string;
  name: string;
  rssi: number;
  connected: boolean;
  gymId: string;
  wallLabel: string;
  firmwareVersion?: string;
  lastSeen: number;
}

/** Physics constants — match aria_models/state_machine.py */
export const TENSION_BASELINE_N = 40.0;
export const TENSION_TAKE_THRESHOLD_N = 200.0;
export const TENSION_FALL_THRESHOLD_N = 400.0;
export const ROPE_SPEED_FALL_MS = 2.0;

// ─── Firestore collection names ───────────────────────────────────────────────
export const COLLECTIONS = {
  GYMS: 'gyms',
  USERS: 'users',
  DEVICES: 'devices',
  SESSIONS: 'sessions',
  INCIDENTS: 'incidents',
  COMMANDS: 'commands',
  LEADERBOARD: 'leaderboard',
} as const;

// ─── Re-export Session so screens can import from types/aria ──────────────────
export type { Session, TensionSample, HeightSample, SessionEvent, SessionEventType } from './session';

// ─── Incident ─────────────────────────────────────────────────────────────────
export interface Incident {
  incidentId: string;
  gymId: string;
  deviceId: string;
  type: 'zone_intrusion' | 'device_offline' | 'fall_detected' | string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: Date;
  resolved: boolean;
  resolvedBy: string | null;
  resolvedAt?: Date;
  notes?: string;
  cameraThumbUrl?: string;
}

// ─── MaintenanceAction ────────────────────────────────────────────────────────
export interface MaintenanceAction {
  actionId: string;
  deviceId: string;
  gymId: string;
  type: 'inspection' | 'rope_replace' | 'brake_service' | 'calibration' | 'firmware_update';
  performedBy: string;
  performedAt: Date;
  notes?: string;
  passed: boolean;
}
