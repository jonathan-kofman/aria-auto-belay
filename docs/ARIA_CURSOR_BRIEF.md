# ARIA Climb — Cursor Project Brief
## React Native App — Build Instructions for AI-Assisted Development

> This document is the authoritative build guide for Cursor. Follow it exactly.
> Do not invent structure, package choices, or naming conventions not listed here.
> When something is marked PHASE 1, build it now. PHASE 2+ means scaffold the file but leave it empty.

---

## WHAT YOU ARE BUILDING

A React Native app called **ARIA Climb** for a hardware auto belay device used in climbing gyms. The app has two modes driven by user role:

- **Gym Mode** — used by gym staff on an iPad. Monitors ARIA hardware devices in real time over BLE, manages routes, views session history, handles safety alerts.
- **Climber Mode** — used by individual climbers on a phone. Views personal session stats, leaderboards, books wall time, syncs preferences to hardware.

One codebase, one app, two experiences. Role is determined at login from Firebase.

---

## EXACT PACKAGE VERSIONS — USE THESE, NO OTHERS

```json
{
  "expo": "~51.0.0",
  "react": "18.2.0",
  "react-native": "0.74.0",
  "react-native-ble-plx": "^3.1.2",
  "@react-navigation/native": "^6.1.17",
  "@react-navigation/bottom-tabs": "^6.5.20",
  "@react-navigation/drawer": "^6.6.15",
  "@react-navigation/stack": "^6.3.29",
  "@react-native-firebase/app": "^20.3.0",
  "@react-native-firebase/auth": "^20.3.0",
  "@react-native-firebase/firestore": "^20.3.0",
  "@react-native-firebase/messaging": "^20.3.0",
  "@react-native-firebase/storage": "^20.3.0",
  "zustand": "^4.5.2",
  "nativewind": "^4.0.1",
  "tailwindcss": "^3.4.3",
  "victory-native": "^41.0.0",
  "i18next": "^23.11.5",
  "react-i18next": "^14.1.2",
  "react-native-mmkv": "^2.12.2",
  "date-fns": "^3.6.0",
  "expo-dev-client": "~4.0.0"
}
```

**Note:** This project uses `expo-dev-client` (NOT Expo Go) because `react-native-ble-plx` requires native modules. Run with `npx expo run:ios` or `npx expo run:android`.

---

## EXACT FOLDER STRUCTURE — CREATE THIS EXACTLY

```
aria-climb/
├── app.json
├── App.tsx                          # Root — loads fonts, sets up providers, routes to RootNavigator
├── babel.config.js
├── tailwind.config.js
├── tsconfig.json
├── .env                             # Firebase config keys — never commit
│
├── src/
│   ├── navigation/
│   │   ├── RootNavigator.tsx        # Checks auth + role, routes to GymNavigator or ClimberNavigator
│   │   ├── GymNavigator.tsx         # iPad drawer navigator for gym staff
│   │   ├── ClimberNavigator.tsx     # Phone bottom tab navigator for climbers
│   │   └── AuthNavigator.tsx        # Login / signup screens
│   │
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── LoginScreen.tsx
│   │   │   ├── SignupScreen.tsx
│   │   │   └── RoleSelectScreen.tsx  # After signup: select gym owner / climber / guest
│   │   │
│   │   ├── gym/
│   │   │   ├── DashboardScreen.tsx   # Device grid — main gym screen
│   │   │   ├── DeviceDetailScreen.tsx
│   │   │   ├── SessionHistoryScreen.tsx
│   │   │   ├── RouteManagementScreen.tsx
│   │   │   ├── DeviceSettingsScreen.tsx
│   │   │   └── AlertHistoryScreen.tsx
│   │   │
│   │   └── climber/
│   │       ├── HomeScreen.tsx        # Wall status + booking
│   │       ├── SessionsScreen.tsx    # Personal session history
│   │       ├── SessionDetailScreen.tsx
│   │       ├── LeaderboardScreen.tsx
│   │       └── ProfileScreen.tsx
│   │
│   ├── components/
│   │   ├── shared/
│   │   │   ├── ARIAStatusBadge.tsx   # IDLE / CLIMBING / PAUSED / ALERT badge
│   │   │   ├── TensionGraph.tsx      # Victory Native line chart
│   │   │   ├── AlertBanner.tsx       # Slides in from top on zone intrusion
│   │   │   ├── OfflineBanner.tsx     # Subtle bar shown when no WiFi
│   │   │   └── LoadingSpinner.tsx
│   │   │
│   │   ├── gym/
│   │   │   ├── DeviceCard.tsx        # Single ARIA unit card on dashboard grid
│   │   │   ├── StateMachineViz.tsx   # Current state + last 5 transitions
│   │   │   ├── CameraThumb.tsx       # Low-res OV2640 preview
│   │   │   └── CalibrationWizard.tsx
│   │   │
│   │   └── climber/
│   │       ├── SessionCard.tsx
│   │       ├── PersonalBestCard.tsx
│   │       ├── LeaderboardRow.tsx
│   │       └── BookingCard.tsx
│   │
│   ├── store/
│   │   ├── authStore.ts              # Zustand — user, role, gymId
│   │   ├── bleStore.ts               # Zustand — connected devices, live readings
│   │   ├── alertStore.ts             # Zustand — active alerts queue
│   │   └── sessionStore.ts           # Zustand — current session buffer
│   │
│   ├── services/
│   │   ├── firebase/
│   │   │   ├── auth.ts               # signIn, signUp, signOut, onAuthStateChanged
│   │   │   ├── firestore.ts          # typed read/write helpers for all collections
│   │   │   ├── notifications.ts      # FCM token registration, notification handlers
│   │   │   └── storage.ts            # camera thumb upload/download
│   │   │
│   │   └── ble/
│   │       ├── bleManager.ts         # BleManager singleton, scan, connect, disconnect
│   │       ├── bleCharacteristics.ts # UUID constants + read/write/notify helpers
│   │       └── bleSessionSync.ts     # Read session data from device, write to Firebase
│   │
│   ├── hooks/
│   │   ├── useARIADevice.ts          # Subscribe to live BLE data for one device
│   │   ├── useSessionHistory.ts      # Firestore query hook for session list
│   │   ├── useLeaderboard.ts         # Firestore query hook for leaderboard
│   │   ├── useAlerts.ts              # Firestore + BLE alert subscription
│   │   └── useNetworkStatus.ts       # NetInfo wrapper, drives OfflineBanner
│   │
│   ├── types/
│   │   ├── device.ts                 # ARIADevice, ARIAState, ARIASettings types
│   │   ├── session.ts                # Session, TensionSample, SessionEvent types
│   │   ├── user.ts                   # User, UserRole, ClimberProfile types
│   │   ├── alert.ts                  # Alert, AlertType types
│   │   └── navigation.ts             # RootStackParamList + all navigator param lists
│   │
│   ├── locales/
│   │   ├── en.json                   # English — source of truth
│   │   ├── es.json                   # Spanish (scaffold empty keys)
│   │   ├── fr.json                   # French (scaffold empty keys)
│   │   ├── de.json                   # German (scaffold empty keys)
│   │   └── ja.json                   # Japanese (scaffold empty keys)
│   │
│   └── utils/
│       ├── formatters.ts             # formatTension(), formatHeight(), formatDuration()
│       ├── blePacketParser.ts        # Parse UART-style packets from BLE notify
│       └── constants.ts              # App-wide constants (timeouts, defaults, etc.)
```

---

## TYPESCRIPT TYPES — DEFINE THESE EXACTLY

### `src/types/device.ts`
```typescript
export type ARIAState =
  | 'IDLE'
  | 'CLIMBING'
  | 'CLIPPING'
  | 'TAKE'
  | 'REST'
  | 'LOWER'
  | 'WATCH_ME'
  | 'CLIMBING_PAUSED';  // zone intrusion sub-state

export interface ARIADevice {
  id: string;                // Firestore deviceId = BLE device ID
  gymId: string;
  name: string;              // e.g. "Route 3 — 5.11b"
  routeName: string;
  grade: string;
  wallSection: string;
  firmwareVersion: string;
  lastSeen: Date;
  isOnline: boolean;
  bleConnected: boolean;
  settings: ARIASettings;
  // Live BLE data — not persisted to Firestore
  liveState?: ARIAState;
  liveTension?: number;      // kN
  liveHeightMeters?: number;
  zoneIntrusionActive?: boolean;
  activeClimberName?: string;
}

export interface ARIASettings {
  tensionSensitivity: number;       // 1–10
  slackAggressiveness: 'conservative' | 'balanced' | 'responsive';
  zoneThresholdSeconds: number;     // 5–30, default 10
  motorKp?: number;                 // Owner only
  motorKi?: number;
  motorKd?: number;
}
```

### `src/types/session.ts`
```typescript
export interface TensionSample {
  t: number;        // unix ms
  tension: number;  // kN
}

export interface HeightSample {
  t: number;
  height: number;   // meters
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
```

### `src/types/user.ts`
```typescript
export type UserRole = 'owner' | 'staff' | 'climber' | 'guest';

export interface User {
  uid: string;
  displayName: string;
  email: string;
  role: UserRole;
  homeGymId: string;
  certifiedLead: boolean;
  preferences: ClimberPreferences;
  language?: string;        // ISO 639-1 code, overrides device locale
  unitSystem?: 'metric' | 'imperial';
}

export interface ClimberPreferences {
  tensionSensitivity: number;       // 1–10
  slackAggressiveness: 'conservative' | 'balanced' | 'responsive';
}
```

### `src/types/alert.ts`
```typescript
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
  acknowledgedBy?: string;   // staff uid
  acknowledgedAt?: Date;
  cameraThumbUrl?: string;   // Firebase Storage URL
}
```

---

## BLE CONSTANTS — `src/services/ble/bleCharacteristics.ts`

```typescript
// ARIA Climb BLE UUIDs
export const ARIA_SERVICE_UUID = '12345678-1234-1234-1234-123456789abc';

export const ARIA_CHARS = {
  STATE:    '12345678-1234-1234-1234-000000000001',  // notify — ARIAState string
  TENSION:  '12345678-1234-1234-1234-000000000002',  // notify — float32 kN
  ENCODER:  '12345678-1234-1234-1234-000000000003',  // notify — float32 meters
  ALERT:    '12345678-1234-1234-1234-000000000004',  // notify — alert packet string
  COMMAND:  '12345678-1234-1234-1234-000000000005',  // write  — command string
  PROFILE:  '12345678-1234-1234-1234-000000000006',  // write  — JSON profile
  SESSION:  '12345678-1234-1234-1234-000000000007',  // read   — JSON session data
} as const;

// BLE packet format helpers
// Alert packets from ARIA_ALERT_CHAR follow format: "TYPE:FIELD:VALUE"
// Examples: "W:ZONE_INTRUSION:ALERT", "W:FALL_DETECTED:CAMERA", "S:SESSION_START:0"
export function parseARIAPacket(raw: string): { type: string; field: string; value: string } {
  const [type, field, value] = raw.split(':');
  return { type, field, value };
}
```

**IMPORTANT:** These UUIDs are placeholders. They must match whatever is assigned in the ESP32-S3 firmware. Do not change them without updating both sides.

---

## FIREBASE SCHEMA — EXACT FIELD NAMES AND TYPES

### `/gyms/{gymId}`
```typescript
{
  name: string,
  address: string,
  ownerUid: string,
  createdAt: Timestamp,
  defaultLanguage: string,    // ISO 639-1, default 'en'
}
```

### `/gyms/{gymId}/devices/{deviceId}`
```typescript
{
  name: string,
  routeName: string,
  grade: string,
  wallSection: string,
  firmwareVersion: string,
  lastSeen: Timestamp,
  isOnline: boolean,
  isEnabled: boolean,
  settings: {
    tensionSensitivity: number,
    slackAggressiveness: 'conservative' | 'balanced' | 'responsive',
    zoneThresholdSeconds: number,
    motorKp: number | null,
    motorKi: number | null,
    motorKd: number | null,
  }
}
```

### `/gyms/{gymId}/devices/{deviceId}/sessions/{sessionId}`
```typescript
{
  climberId: string,
  climberName: string,
  startTime: Timestamp,
  endTime: Timestamp,
  durationSeconds: number,
  maxHeightMeters: number,
  clipCount: number,
  fallCount: number,
  tensionTrace: Array<{ t: number, tension: number }>,
  heightTrace: Array<{ t: number, height: number }>,
  events: Array<{ t: number, type: string, value: number | null }>,
}
```

### `/gyms/{gymId}/alerts/{alertId}`
```typescript
{
  deviceId: string,
  deviceName: string,
  type: 'zone_intrusion' | 'device_offline' | 'fall_detected',
  startTime: Timestamp,
  endTime: Timestamp | null,
  resolvedBy: 'auto_clear' | 'voice_override' | 'staff_dismiss' | null,
  acknowledgedBy: string | null,
  acknowledgedAt: Timestamp | null,
  cameraThumbUrl: string | null,
}
```

### `/users/{uid}`
```typescript
{
  displayName: string,
  email: string,
  role: 'owner' | 'staff' | 'climber' | 'guest',
  homeGymId: string,
  certifiedLead: boolean,
  language: string,
  unitSystem: 'metric' | 'imperial',
  preferences: {
    tensionSensitivity: number,
    slackAggressiveness: 'conservative' | 'balanced' | 'responsive',
  },
  fcmToken: string | null,
}
```

### `/users/{uid}/sessions/{sessionId}`
```typescript
// Mirror of device session — same shape, add gymId and routeName
{
  gymId: string,
  deviceId: string,
  routeName: string,
  // ... all fields from device session
}
```

### `/bookings/{bookingId}`
```typescript
{
  gymId: string,
  deviceId: string,
  climberId: string,
  climberName: string,
  scheduledTime: Timestamp,
  durationMinutes: number,
  status: 'pending' | 'confirmed' | 'active' | 'completed' | 'cancelled',
  createdAt: Timestamp,
}
```

---

## ZUSTAND STORES — SHAPE ONLY, IMPLEMENT PHASE 1

### `src/store/authStore.ts`
```typescript
interface AuthState {
  user: User | null;
  isLoading: boolean;
  isGymMode: boolean;       // true if role is owner or staff
  setUser: (user: User | null) => void;
  signOut: () => Promise<void>;
}
```

### `src/store/bleStore.ts`
```typescript
interface BLEState {
  devices: Record<string, ARIADevice>;  // deviceId → live device state
  isScanning: boolean;
  updateDevice: (deviceId: string, patch: Partial<ARIADevice>) => void;
  removeDevice: (deviceId: string) => void;
}
```

### `src/store/alertStore.ts`
```typescript
interface AlertState {
  activeAlerts: Alert[];
  addAlert: (alert: Alert) => void;
  dismissAlert: (alertId: string) => void;
  clearAlert: (alertId: string) => void;
}
```

### `src/store/sessionStore.ts`
```typescript
interface SessionState {
  currentSession: Partial<Session> | null;
  tensionBuffer: TensionSample[];
  heightBuffer: HeightSample[];
  eventBuffer: SessionEvent[];
  startSession: (deviceId: string, climberId: string) => void;
  endSession: () => Promise<void>;
  addTensionSample: (sample: TensionSample) => void;
  addEvent: (event: SessionEvent) => void;
}
```

---

## NAVIGATION STRUCTURE

### `RootNavigator.tsx` logic:
```
if (!user) → AuthNavigator
if (user && isGymMode) → GymNavigator
if (user && !isGymMode) → ClimberNavigator
```

### `AuthNavigator` (Stack):
```
Login → Signup → RoleSelect
```

### `GymNavigator` (Drawer, iPad sidebar):
```
Dashboard          (default)
Session History
Route Management
Alert History
Settings
```
Each drawer item can push a Stack for detail views (e.g. Dashboard → DeviceDetail).

### `ClimberNavigator` (Bottom Tabs, Phone):
```
Tab 1: Home        (HomeScreen)
Tab 2: Sessions    (SessionsScreen → SessionDetailScreen via stack)
Tab 3: Leaderboard (LeaderboardScreen)
Tab 4: Profile     (ProfileScreen)
```

### Navigation param types — `src/types/navigation.ts`:
```typescript
export type RootStackParamList = {
  Auth: undefined;
  Gym: undefined;
  Climber: undefined;
};

export type AuthStackParamList = {
  Login: undefined;
  Signup: undefined;
  RoleSelect: undefined;
};

export type GymDrawerParamList = {
  Dashboard: undefined;
  DeviceDetail: { deviceId: string };
  SessionHistory: { deviceId?: string };
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

export type ClimberStackParamList = {
  SessionList: undefined;
  SessionDetail: { sessionId: string };
};
```

---

## i18n SETUP

### `src/locales/en.json` — all keys must exist here first:
```json
{
  "common": {
    "loading": "Loading...",
    "error": "Something went wrong",
    "retry": "Try again",
    "offline": "Offline — changes will sync when connected",
    "save": "Save",
    "cancel": "Cancel",
    "confirm": "Confirm"
  },
  "auth": {
    "login": "Log in",
    "signup": "Sign up",
    "email": "Email",
    "password": "Password",
    "logout": "Log out"
  },
  "device": {
    "states": {
      "IDLE": "Idle",
      "CLIMBING": "Climbing",
      "CLIPPING": "Clipping",
      "TAKE": "Take",
      "REST": "Resting",
      "LOWER": "Lowering",
      "WATCH_ME": "Watch Me",
      "CLIMBING_PAUSED": "Paused"
    },
    "tension": "Tension",
    "height": "Height",
    "connected": "Connected",
    "disconnected": "Disconnected"
  },
  "alerts": {
    "zone_intrusion": "Fall zone occupied",
    "device_offline": "Device offline",
    "fall_detected": "Fall detected",
    "motor_paused": "Motor paused",
    "zone_cleared": "Zone cleared — resuming",
    "say_to_resume": "Say \"climbing\" to resume"
  },
  "gym": {
    "dashboard": "Dashboard",
    "sessions": "Sessions",
    "routes": "Routes",
    "settings": "Settings",
    "alerts": "Alerts"
  },
  "climber": {
    "home": "Home",
    "my_sessions": "My Sessions",
    "leaderboard": "Leaderboard",
    "profile": "Profile",
    "book_wall": "Book Wall",
    "personal_bests": "Personal Bests",
    "max_height": "Max Height",
    "total_clips": "Total Clips",
    "total_falls": "Total Falls"
  }
}
```

All other locale files (`es.json`, `fr.json`, etc.) have the same key structure with empty string values for now. Do not leave keys missing — use `""` as placeholder.

---

## FORMATTERS — `src/utils/formatters.ts`

```typescript
// Always use these, never format inline in components

export function formatTension(kn: number, unitSystem: 'metric' | 'imperial' = 'metric'): string {
  // metric: "3.2 kN", imperial: "719 lbf"
}

export function formatHeight(meters: number, unitSystem: 'metric' | 'imperial' = 'metric'): string {
  // metric: "12.4 m", imperial: "40.7 ft"
}

export function formatDuration(seconds: number): string {
  // "4m 32s" or "1h 12m"
}

export function formatDate(date: Date, locale?: string): string {
  // Uses Intl.DateTimeFormat with device locale
}
```

---

## OFFLINE PERSISTENCE — ENABLE IN APP.TSX

```typescript
import firestore from '@react-native-firebase/firestore';

// Call once at app startup, before any Firestore reads
firestore().settings({
  persistence: true,   // Enable offline cache
  cacheSizeBytes: firestore.CACHE_SIZE_UNLIMITED,
});
```

---

## WHAT TO BUILD IN PHASE 1 (BUILD THIS NOW)

Phase 1 is auth + skeleton navigation + type definitions. Everything compiles, navigates correctly, shows placeholder content. No real BLE, no real Firebase reads yet except auth.

1. Create the full folder structure above — all files, even if empty
2. Install all packages from the package list
3. Define all types in `src/types/`
4. Set up `i18next` with `en.json`, scaffold other locale files with empty values
5. Implement `authStore` with Zustand
6. Implement `AuthNavigator` with working Login screen (Firebase Auth email/password)
7. Implement `RootNavigator` role-based routing
8. Implement `GymNavigator` drawer with placeholder screens
9. Implement `ClimberNavigator` bottom tabs with placeholder screens
10. Implement `formatters.ts` with all four functions
11. Enable Firestore offline persistence in `App.tsx`
12. Create `bleCharacteristics.ts` with UUIDs and `parseARIAPacket`

**Phase 1 done = app launches, you can log in, role routes you to the right navigator, all screens exist (even if blank), TypeScript compiles with zero errors.**

---

## WHAT TO SCAFFOLD BUT NOT IMPLEMENT YET (PHASE 2+)

Create the file, export an empty component or empty function, add a `// TODO: Phase N` comment. Do not implement.

- `bleManager.ts` — TODO: Phase 2
- `bleSessionSync.ts` — TODO: Phase 3
- `DeviceCard.tsx` — TODO: Phase 2
- `StateMachineViz.tsx` — TODO: Phase 2
- `TensionGraph.tsx` — TODO: Phase 2
- `CameraThumb.tsx` — TODO: Phase 4
- `CalibrationWizard.tsx` — TODO: Phase 2
- `AlertBanner.tsx` — TODO: Phase 4
- `useARIADevice.ts` — TODO: Phase 2
- `useLeaderboard.ts` — TODO: Phase 5
- `bleStore.ts` — TODO: Phase 2
- `alertStore.ts` — TODO: Phase 4
- `sessionStore.ts` — TODO: Phase 3

---

## RULES FOR CURSOR

1. **Never hardcode English strings in components.** Always use `useTranslation()` and a key from `en.json`.
2. **Never format numbers or units inline.** Always use `formatTension()`, `formatHeight()`, `formatDuration()`.
3. **Never access Firestore directly in a component.** All Firestore operations go through `src/services/firebase/firestore.ts`.
4. **Never access BLE directly in a component.** All BLE operations go through `src/services/ble/bleManager.ts`.
5. **All components are functional with hooks.** No class components.
6. **All files are TypeScript.** No `.js` files except config files.
7. **iPad vs. phone layout** is handled in the component using `useWindowDimensions()`. Do not create separate files for iPad/phone variants.
8. **Zustand stores are the only global state.** Do not use React Context for app state.
9. **When in doubt about a UI decision, leave a `// TODO: design` comment and move on.** Don't invent UI that isn't specified here.
