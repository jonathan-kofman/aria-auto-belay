export type UserRole = 'owner' | 'staff' | 'climber' | 'guest';

export interface User {
  uid: string;
  displayName: string;
  email: string;
  role: UserRole;
  homeGymId: string;
  certifiedLead: boolean;
  preferences: ClimberPreferences;
  language?: string;
  unitSystem?: 'metric' | 'imperial';
}

export interface ClimberPreferences {
  tensionSensitivity: number;
  slackAggressiveness: 'conservative' | 'balanced' | 'responsive';
}
