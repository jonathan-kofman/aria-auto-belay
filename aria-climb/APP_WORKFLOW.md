# ARIA Climb — App workflow (everything working together)

Use this to verify the app flows without real ARIA hardware, and to test safety/camera monitoring.

---

## 1. Run the app

```bash
cd aria-climb
npm install --legacy-peer-deps
npx expo run:android
# or: npx expo run:ios
```

You need a dev client build (Expo Go won’t work for BLE/camera). Add Firebase config (`google-services.json` for Android) if you use auth/Firestore.

**Why does the app look the same / stay on Sign up?** The app only shows the main screens (Gym, Safety / Camera test, etc.) after you're signed in. If sign-up fails with `firestore/permission-denied`, you never get past the Sign up screen. Fix Firestore rules (see below), then sign up again. To see code changes: use **Reload** in the dev menu (shake device or Ctrl+M), or in the terminal press `r` when Metro is running.

**`firestore/permission-denied` when adding a profile:** Sign-up writes a profile to Firestore at `users/{uid}`. Your Firestore rules must allow that. In [Firebase Console](https://console.firebase.google.com): your project → Firestore Database → Rules. Paste the contents of `aria-climb/firestore.rules` and click **Publish**. Then try sign up again.

**Main pages still look plain or not updating?** (1) **Reload the bundle:** shake device (or Ctrl+M) → **Reload**. (2) **Clear Metro cache:** stop the dev server, then run `npx expo start --clear` and open the app again. (3) After changing native code or adding packages, rebuild: `npx expo run:android`. The Gym screens use a dark header/drawer theme (#1a1a2e); if you only see white headers, the app is likely loading an old bundle — use step 1 or 2.

---

## 2. Safety & camera test (no hardware)

1. Log in and open **Gym** mode (drawer).
2. In the drawer, open **Safety / Camera test**.
3. **Camera**
   - If you see “Install expo-camera”: run `npx expo install expo-camera` in the project folder, then rebuild (`npx expo run:android`). After that, request camera permission and you should see a live preview.
   - If you already have expo-camera: tap **Request camera permission**, then confirm the preview appears.
4. **Mock zone intrusion**
   - Tap **Simulate zone intrusion**.
   - You should see:
     - Red **alert banner** at the top of the Gym screens (“Fall zone occupied (mock)”).
     - In the drawer, open **Alert history** — the first row should be “(mock) · zone_intrusion · Fall zone occupied — from Safety / Camera test”.
   - Tap **Clear zone** (in the banner or on the Safety / Camera test screen) to clear the mock.

This is the same flow as real hardware: zone event → banner + alert history.

---

## 3. What to verify (checklist)

| Step | What to check |
|------|----------------|
| Camera | Permission granted; live preview shows when expo-camera is installed and permission granted. |
| Mock zone | “Simulate zone intrusion” shows the red banner at top of Gym UI. |
| Alert history | With mock active, Alert history shows the mock zone_intrusion row at the top. |
| Clear | “Clear zone” dismisses the banner and the mock row is no longer “active now”. |

---

## 4. Expo camera install (live preview in Safety / Camera test)

If the Safety / Camera test screen shows “Install expo-camera”:

1. **Install** (from `aria-climb` folder): `npx expo install expo-camera`
2. **Rebuild** (required for native modules): `npx expo run:android` (or `run:ios`)
3. In the app: Gym → **Safety / Camera test** → **Request camera permission**. When granted, the back-camera preview appears.

If expo-camera is already in package.json, run `npm install` then `npx expo run:android` again. Camera permissions are configured in `app.json`.

**Android build needs Java:** If `npx expo run:android` fails with "JAVA_HOME is not set", install JDK 17 (e.g. [Microsoft OpenJDK](https://learn.microsoft.com/en-us/java/openjdk/download#openjdk-17)), then set `JAVA_HOME` to the JDK folder and add `%JAVA_HOME%\bin` to your PATH. Restart the terminal and run the build again.

---

## 5. With real hardware later

- **BLE**: Use **Provisioning** to set up devices; dashboard and device detail will use live BLE when connected.
- **Zone intrusion**: When the device sends a real zone event, the same **AlertBanner** and **Alert history** flow will be used (backend/Firebase can feed real incidents into the same UI).
- **Camera**: On-device CV runs on the ESP32; the app’s camera test is for verifying tablet/phone camera for future features (e.g. thumbnails, verification).

---

## Quick reference

| Goal | Where to go |
|------|-------------|
| Test camera + mock zone flow | Gym → **Safety / Camera test** |
| See alerts (mock or real) | Gym → **Alert history** |
| Device list and detail | Gym → **Dashboard** → tap a device |
| Provision new devices | Gym → **Provisioning** |
| Safety settings (auto-pause on zone, etc.) | Gym → **Settings** |
