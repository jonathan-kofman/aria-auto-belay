export interface TensionSample {
  t: number;
  tension: number;
}

export interface HeightSample {
  t: number;
  height: number;
}

export type SessionEventType = 'clip' | 'fall' | 'zone_intrusion' | 'pause' | 'resume';

export interface SessionEvent {
  t: number;
  type: SessionEventType;
  value?: number;
}

export interface Session {
  id: string;
  gymId: string;
  deviceId: string;
  routeName: string;
  climberId: string;
  climberName: string;
  startTime: Date;
  endTime: Date;
  durationSeconds: number;
  maxHeightMeters: number;
  clipCount: number;
  fallCount: number;
  tensionTrace: TensionSample[];
  heightTrace: HeightSample[];
  events: SessionEvent[];
}
