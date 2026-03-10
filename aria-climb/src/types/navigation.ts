export type RootStackParamList = {
  Auth: undefined;
  Gym: undefined;
  Climber: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  Signup: undefined;
  RoleSelect: undefined;
  ClaimGym: undefined;
};

export type GymDrawerParamList = {
  Dashboard: undefined;
  DashboardHome: undefined;
  DeviceDetail: { deviceId: string };
  DeviceHealth: { deviceId: string };
  SessionHistory: { deviceId?: string };
  Provisioning: undefined;
  SafetyCameraTest: undefined;
  RouteManagement: undefined;
  AlertHistory: undefined;
  Settings: { deviceId?: string };
};

export type ClimberTabParamList = {
  Home: undefined;
  Sessions: undefined;
  Leaderboard: undefined;
  Profile: undefined;
};

export type ClimberDrawerParamList = {
  Home: undefined;
  Sessions: undefined;
  Leaderboard: undefined;
  Profile: undefined;
};

export type ClimberStackParamList = {
  SessionList: undefined;
  SessionDetail: { sessionId: string };
};
