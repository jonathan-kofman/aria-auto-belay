# ARIA Mobile App Specification
## React Native — iOS / Android / iPadOS

**Document Version:** 0.2  
**Status:** Architecture — Decisions Locked  
**App Store / Play Store Name:** ARIA Climb  
**Stack:** React Native + Firebase + BLE (react-native-ble-plx)  
**Repository:** TBD (separate from firmware repo)

---

## 1. Overview

The ARIA app is a single React Native application that serves two distinct audiences on the same codebase: **gym staff** managing devices from an iPad, and **climbers** tracking their sessions from a phone. The app mode is determined by the user's role at login. Communication with ARIA hardware uses BLE for real-time control and alerts; all persistent data syncs to Firebase after each session.

---

## 2. User Roles

| Role | Access | Primary Device |
|---|---|---|
| Gym Owner / Staff | Full control — all devices, all settings, all history, calibration | iPad |
| Certified Lead Climber | Personal settings, session history, leaderboards, wall booking | Phone |
| Guest / Drop-in | View-only — leaderboard, active session status, wall availability | Phone |

Role is assigned at account creation and can be upgraded by a Gym Owner. A gym may have multiple staff accounts but only one Owner account per gym.

---

## 3. App Modes

### 3.1 Gym Mode (iPad)

Activated when a Staff or Owner account logs in on an iPad. Layout adapts to iPad screen — dashboard-first, sidebar navigation, multi-panel views.

**Dashboard (home screen)**
- Grid of all ARIA units assigned to this gym, each showing:
  - Device name / route name
  - Current state (IDLE / CLIMBING / PAUSED / ALERT)
  - Active climber name (if BLE-identified)
  - Session duration
  - Live tension reading
  - Zone intrusion status (green / red indicator)
- Tap any unit card to open the device detail view

**Device Detail View**
- Live state machine visualization — current state highlighted, last 5 transitions logged
- Real-time rope tension graph (last 60 seconds)
- Encoder position / rope payout
- Zone camera feed thumbnail (low-res live preview from OV2640)
- Active alerts with timestamp and dismiss button
- Quick controls: force IDLE, force LOWER, emergency stop

**Zone Intrusion Alert Handling**
- Alert banner slides in from top on any zone intrusion across any device
- Shows: device name, duration of intrusion, camera thumbnail
- Staff can dismiss (acknowledge) or view full detail
- Alert history log with timestamps, duration, resolution (auto-cleared vs. voice override)

**Session History**
- Per-device or per-climber view
- Each session shows: climber name, date/time, max height reached, number of clips, number of falls, session duration
- Filterable by device, date range, climber
- Exportable as CSV (for gym liability records)

**Route Management**
- Assign each ARIA unit a route name, wall section, and difficulty grade
- Set route-specific parameters: expected bolt spacing, max route height (used to validate encoder calibration)
- Enable / disable specific ARIA units without touching the device

**Device Settings / Calibration**
- Tension sensitivity: slider (1–10), maps to load cell threshold multipliers
- Slack aggressiveness: conservative / balanced / responsive
- Zone intrusion threshold: adjustable 5–30s (default 10s)
- Motor PID parameters: Kp, Ki, Kd (advanced — Owner only, not Staff)
- Re-run calibration sequence: walks staff through rope threading and encoder zeroing
- Firmware version display and OTA update trigger (future)

**Multi-Device Dashboard**
- Gym Owner only: view all devices across multiple locations if gym has multiple sites
- Per-location health summary: devices online, devices in alert, active sessions

---

### 3.2 Climber Mode (Phone)

Activated when a Certified Climber or Guest account logs in on a phone. Bottom tab navigation, portrait-optimized.

**Home Tab**
- Wall status cards: which routes have ARIA installed, current availability (idle / occupied), estimated wait if occupied
- Book a session: reserve the wall up to 24 hours ahead (Certified Climbers only)
- Active session card: if currently climbing, shows live stats — height, clips, time on wall

**My Sessions Tab**
- Chronological session history with key stats per session
- Session detail: height-over-time graph, clip events marked on timeline, fall events marked
- Personal bests: max height, most clips in a session, longest session
- Shareable session summary card (image export for Instagram etc.)

**Leaderboard Tab**
- Gym-wide leaderboard, filterable by:
  - Route (specific wall)
  - Time period (this week / this month / all time)
  - Metric (max height / most clips / most sessions)
- Friends leaderboard (follow other climbers)
- Guest users can view but not appear on leaderboard

**Profile / Settings Tab**
- Display name, profile photo
- Home gym selection
- Personal ARIA preferences (synced to device at session start via BLE):
  - Tension sensitivity preference
  - Slack aggressiveness preference
- Notification settings: booking reminders, session summaries, leaderboard updates
- Lead certification status (verified by gym staff)

---

## 4. BLE Architecture

ARIA communicates with the app over BLE. The iPad in Gym Mode maintains a persistent BLE connection to all nearby ARIA units. Climber phones connect briefly at session start/end for profile sync.

### BLE Services

```
ARIA BLE Service UUID: [TBD — assign on ESP32-S3]

Characteristics:
  ARIA_STATE_CHAR        — notify — current state machine state (read every 500ms)
  ARIA_TENSION_CHAR      — notify — live tension value (read every 200ms)
  ARIA_ENCODER_CHAR      — notify — rope payout position (read every 200ms)
  ARIA_ALERT_CHAR        — notify — alert events (zone intrusion, fall, etc.)
  ARIA_COMMAND_CHAR      — write  — send commands to device (force state, settings)
  ARIA_PROFILE_CHAR      — write  — write climber profile at session start
  ARIA_SESSION_CHAR      — read   — read completed session data at session end
```

### iPad Connection Management
- iPad app maintains persistent BLE connections to all ARIA units in range
- Auto-reconnects on disconnect (device power cycle, BLE range loss)
- Connection status shown per-device on dashboard
- If BLE connection lost during active climb: device continues operating autonomously on last known parameters, app shows "BLE DISCONNECTED" warning

### Climber Phone Connection Flow
1. Climber opens app near wall → app scans for ARIA BLE advertisement
2. Finds device → connects → writes profile to ARIA_PROFILE_CHAR
3. ARIA loads profile, ESP32 sends `I:CLIMBER_ID:profile_hash` to STM32
4. Phone disconnects (iPad takes over monitoring)
5. After session: phone reconnects → reads ARIA_SESSION_CHAR → syncs to Firebase → disconnects

---

## 5. Firebase Data Architecture

### Collections

```
/gyms/{gymId}
  name, address, ownerUid, createdAt

/gyms/{gymId}/devices/{deviceId}
  name, routeName, grade, wallSection
  firmwareVersion, lastSeen, isOnline
  settings: { tensionSensitivity, slackAggressiveness, zoneThresholdSeconds }

/gyms/{gymId}/devices/{deviceId}/sessions/{sessionId}
  climberId, climberName
  startTime, endTime, durationSeconds
  maxHeightMeters
  clipCount, fallCount
  tensionTrace: [ { t, tension } ]   // downsampled, ~1 point/sec
  heightTrace: [ { t, height } ]
  events: [ { t, type, value } ]     // clip, fall, zone_intrusion, pause

/gyms/{gymId}/alerts/{alertId}
  deviceId, type, startTime, endTime
  acknowledgedBy, acknowledgedAt
  cameraThumb: base64 string (small JPEG from OV2640 at alert trigger)

/users/{uid}
  displayName, email, role, homeGymId
  certifiedLead: boolean
  preferences: { tensionSensitivity, slackAggressiveness }

/users/{uid}/sessions/{sessionId}
  gymId, deviceId, routeName
  — mirrors device session data for climber-facing queries

/bookings/{bookingId}
  gymId, deviceId, climberId, scheduledTime, durationMinutes, status
```

### Firebase Services Used
- **Authentication** — email/password + optional Google sign-in
- **Firestore** — all persistent data (sessions, alerts, settings, users)
- **Cloud Functions** — session processing (compute stats, update leaderboards, send notifications)
- **Cloud Messaging (FCM)** — push notifications (zone intrusion alerts to staff, booking reminders to climbers)
- **Storage** — camera thumbnails from zone intrusion events

---

## 6. Session Data Flow

```
Climber approaches wall
    │
    ▼
Phone BLE handshake → writes profile to ARIA
    │
    ▼
ARIA session starts — ESP32 begins buffering:
  tension samples, encoder samples, event log
    │
    ▼
iPad monitors in real-time via BLE notify characteristics
    │
    ▼
Session ends (climber lowers, returns to base)
    │
    ├──► ARIA buffers session data in ESP32 RAM
    │
    ├──► Phone reconnects via BLE → reads ARIA_SESSION_CHAR
    │        → writes to /users/{uid}/sessions/{sessionId}
    │        → Cloud Function mirrors to /gyms/.../devices/.../sessions/
    │
    └──► iPad reads same session char (fallback if phone not present)
             → writes to /gyms/.../devices/.../sessions/
```

If neither phone nor iPad can read session data immediately (BLE gap), ARIA holds session in ESP32 RAM until a connection is established. Sessions are small enough (~5KB typical) to buffer several before overflow is a concern.

---

## 7. Notifications

| Event | Recipient | Delivery |
|---|---|---|
| Zone intrusion (active) | Gym staff on duty | Push + in-app banner |
| Zone intrusion (resolved) | Gym staff | In-app only |
| Device went offline during active session | Gym staff | Push |
| Booking reminder (30 min before) | Climber | Push |
| Session summary | Climber | Push + in-app |
| New personal best | Climber | Push |
| Leaderboard position change | Climber (opt-in) | Push |
| Firmware update available | Gym Owner | In-app only |

---

## 8. UI Layout Summary

### iPad (Gym Mode) — Landscape

```
┌─────────────────────────────────────────────────────┐
│  ARIA           [Gym Name]              [Staff Name] │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│ Dashboard│   [ Device Grid / Detail Panel ]         │
│ Sessions │                                          │
│ Routes   │                                          │
│ Settings │                                          │
│          │                                          │
└──────────┴──────────────────────────────────────────┘
```

### Phone (Climber Mode) — Portrait

```
┌─────────────────────┐
│   ARIA              │
│   [Home content]    │
│                     │
│                     │
│                     │
├─────────────────────┤
│ Home │ Sessions │ 🏆 │ Profile │
└─────────────────────┘
```

---

## 9. Tech Stack

See Section 14 for full stack detail with resolved decisions.

---

## 10. Development Phases

| Phase | App Deliverable |
|---|---|
| 1 | Auth, user roles, gym + device registration, basic dashboard |
| 2 | BLE connection to ARIA, live state + tension display, device settings |
| 3 | Session recording, session history, climber profile sync |
| 4 | Zone intrusion alerts, push notifications, alert history |
| 5 | Leaderboards, bookings, session sharing, multi-site dashboard |

Phase 1–2 can begin before ARIA hardware is available using the existing `aria_simulator.py` and `aria_test_harness.py` tools to generate realistic BLE-like data for UI development.

---

## 11. Business Model

**App pricing:** ARIA Climb is free — included with device purchase for gyms, free to download for climbers. No SaaS subscription, no in-app purchases.

**Implication for backend costs:** Firebase usage scales with session volume. At early adoption (10–50 gyms), Firebase free tier will likely cover it. Plan for Blaze pay-as-you-go billing once device fleet grows. Session data is small (~5KB/session) so storage costs are negligible; Firestore read/write volume and FCM notifications are the cost drivers to watch.

---

## 12. Offline Mode

Firestore offline persistence is **enabled by default** from day one. This is a single initialization flag and costs nothing. The benefit is complete session data durability when gym WiFi drops mid-climb.

**Behavior with offline persistence enabled:**
- All Firestore reads/writes are mirrored to a local on-device cache
- During WiFi outage: session data writes to local cache, syncs automatically when connectivity returns
- BLE to ARIA continues working regardless of WiFi — device operates normally
- App UI continues to function (reads from cache) with a subtle "offline" indicator

**What still requires connectivity:**
- Push notifications (FCM) — zone intrusion alerts to staff won't deliver if iPad has no internet; mitigated by in-app banner which works locally
- Leaderboard updates — stale while offline, refreshes on reconnect
- Booking confirmation — write queued locally, server confirms when online

---

## 13. Internationalization (i18n)

Multi-language support is built in from the start using `i18next` + `react-i18next`. Adding a new language is adding a JSON translation file — no code changes required.

**Initial launch languages:** English  
**Priority additions:** Spanish, French, German, Japanese (largest climbing gym markets outside English-speaking countries)

**Implementation scope:**

All static UI strings are externalized to translation JSON files — no hardcoded English in components.

Number and unit formatting uses the device locale via `Intl.NumberFormat`:
- Tension readings: locale-appropriate decimal separator (3.2 kN vs. 3,2 kN)
- Heights: metric (meters) globally, imperial (feet) as user preference for US gyms
- Dates/times: locale-appropriate format via `Intl.DateTimeFormat`

Leaderboard and stats displays use locale-aware number formatting throughout.

RTL layout support is handled by React Native's built-in RTL detection — relevant for Arabic and Hebrew if those markets are pursued later.

**Translation file structure:**
```
/locales/
  en.json       // English (source of truth)
  es.json       // Spanish
  fr.json       // French
  de.json       // German
  ja.json       // Japanese
```

Gym Owners can set a default language for their gym (displayed on iPad app). Individual climbers can override with their personal device language preference.

---

## 14. Tech Stack Detail (Updated)

| Layer | Technology |
|---|---|
| App framework | React Native (Expo managed workflow) |
| App name | ARIA Climb |
| BLE | react-native-ble-plx |
| Navigation | React Navigation v6 |
| State management | Zustand |
| Firebase | @react-native-firebase (Auth, Firestore, FCM, Storage) |
| Firestore offline | Enabled by default (`enablePersistence()`) |
| UI components | NativeWind (Tailwind for RN) |
| Charts | Victory Native |
| i18n | i18next + react-i18next |
| Unit formatting | Intl.NumberFormat + Intl.DateTimeFormat (device locale) |
| iPad layout | useWindowDimensions + conditional layouts |

---

## 15. Resolved Design Decisions

| Question | Decision |
|---|---|
| App Store name | ARIA Climb |
| Business model | Free — included with device purchase, free for climbers |
| Offline mode | Firestore offline persistence enabled by default |
| Multi-language | Yes — i18next, English first, ES/FR/DE/JA as priority additions |
| Unit system | Metric globally, imperial as user preference for US gyms |
