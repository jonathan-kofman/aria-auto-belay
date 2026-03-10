# ARIA Climb

React Native app for the ARIA auto belay device — **Gym Mode** (iPad) and **Climber Mode** (phone). One codebase, role determined at login from Firebase.

## Phase 1 (current)

- Auth (Firebase email/password), role select after signup, role-based routing
- Gym Navigator (drawer): Dashboard, Session History, **Safety / Camera test**, Routes, Alerts, Settings
- Climber Navigator (tabs): Home, Sessions, Leaderboard, Profile
- Types, i18n (en + scaffolded es/fr/de/ja), Zustand stores, formatters, BLE UUIDs
- Firestore offline persistence enabled in `App.tsx`

## Setup

1. **Install dependencies** (use legacy peer deps for Victory Native / React 18):
   ```bash
   npm install --legacy-peer-deps
   ```

2. **Firebase**  
   Configure your Firebase project and add native config:
   - **iOS:** `GoogleService-Info.plist` in `ios/` (or use Expo config plugin)
   - **Android:** `google-services.json` in `android/app/`  
   See [Expo + React Native Firebase](https://rnfirebase.io/) for setup.

3. **Run** (requires native build — this app uses `expo-dev-client` and BLE):
   ```bash
   npx expo run:ios
   # or
   npx expo run:android
   ```
   You cannot use Expo Go; use a dev client build.

4. **Optional:** Copy `.env.example` to `.env` and add any Firebase keys if you use env-based config.

**Testing safety monitoring (no hardware):** See [APP_WORKFLOW.md](APP_WORKFLOW.md). Gym → **Safety / Camera test** lets you verify camera permission, optional live preview (with `expo-camera`), and a **mock zone intrusion** that drives the same alert banner and Alert history as real hardware.

## Developing on Windows (no Mac)

- **Android:** Full development on Windows. Install [Android Studio](https://developer.android.com/studio) (with SDK and emulator), then run:
  ```bash
  npx expo run:android
  ```
  Use an emulator or a physical Android device. **Gym Mode** (drawer/tablet UI) can be tested on an Android tablet; same codebase.

- **iOS:** Building or running the iOS app requires Xcode (macOS only). On Windows you have two options when you need iOS:
  1. **Expo EAS Build (recommended):** Build iOS in the cloud. Sign up at [expo.dev](https://expo.dev), then `npx eas build --platform ios`. No Mac required for builds or App Store submission.
  2. Use a Mac (or borrow one) for local `npx expo run:ios` and Simulator.

Until you set up EAS or use a Mac, develop and test on Android only.

## Structure

Follows `docs/ARIA_CURSOR_BRIEF.md` in the parent repo:

- `src/navigation` — Root, Auth, Gym (drawer), Climber (tabs)
- `src/screens/auth` — Login, Signup, RoleSelect
- `src/screens/gym` — Dashboard, Device detail, Session history, Routes, Alerts, Settings
- `src/screens/climber` — Home, Sessions, Leaderboard, Profile
- `src/store` — authStore (Phase 1), bleStore, alertStore, sessionStore (scaffolded)
- `src/services/firebase` — auth, firestore; notifications/storage scaffolded
- `src/services/ble` — bleCharacteristics (UUIDs + parseARIAPacket); bleManager / bleSessionSync scaffolded
- `src/types`, `src/locales`, `src/utils`, `src/components`, `src/hooks` as per brief

## BLE

BLE UUIDs in `src/services/ble/bleCharacteristics.ts` are placeholders and must match your ESP32-S3 firmware.
