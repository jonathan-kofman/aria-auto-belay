export type AlertType = 'zone_intrusion' | 'device_offline' | 'fall_detected';

export interface Alert {
  id: string;
  gymId: string;
  deviceId: string;
  deviceName: string;
  type: AlertType;
  startTime: Date;
  endTime?: Date;
  resolvedBy: 'auto_clear' | 'voice_override' | 'staff_dismiss' | null;
  acknowledgedBy?: string;
  acknowledgedAt?: Date;
  cameraThumbUrl?: string;
}
