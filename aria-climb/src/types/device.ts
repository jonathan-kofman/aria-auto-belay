export type ARIAState =
  | 'IDLE'
  | 'CLIMBING'
  | 'CLIPPING'
  | 'TAKE'
  | 'REST'
  | 'LOWER'
  | 'WATCH_ME'
  | 'CLIMBING_PAUSED';

export interface ARIADevice {
  id: string;
  gymId: string;
  name: string;
  routeName: string;
  grade: string;
  wallSection: string;
  firmwareVersion: string;
  lastSeen: Date;
  isOnline: boolean;
  bleConnected: boolean;
  settings: ARIASettings;
  liveState?: ARIAState;
  liveTension?: number;
  liveHeightMeters?: number;
  zoneIntrusionActive?: boolean;
  activeClimberName?: string;
}

export interface ARIASettings {
  tensionSensitivity: number;
  slackAggressiveness: 'conservative' | 'balanced' | 'responsive';
  zoneThresholdSeconds: number;
  motorKp?: number;
  motorKi?: number;
  motorKd?: number;
}
