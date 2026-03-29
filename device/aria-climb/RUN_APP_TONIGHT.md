# Run ARIA Climb Tonight (Windows + Android)

Follow these steps in order. Allow **30–60 minutes** if you need to install Android Studio.

---

## 1. Prerequisites

### Node.js
- You need Node.js (v18 or v20). You already have it if the Python dashboard runs.
- Check: open PowerShell and run `node -v`. If you see a version, you’re good.

### Android Studio (for emulator or device)
- **Download:** https://developer.android.com/studio  
- **Install** and open Android Studio.
- In the welcome screen: **More Actions** → **SDK Manager** (or **Settings** → **Languages & Frameworks** → **Android SDK**).
  - **SDK Platforms:** enable at least one (e.g. **Android 14.0** or latest).
  - **SDK Tools:** ensure **Android SDK Build-Tools**, **Android Emulator**, **Android SDK Platform-Tools** are checked. Apply/OK.
- **Create an emulator:** **Device Manager** → **Create Device** → pick a phone (e.g. Pixel 7) → pick a system image (e.g. API 34) → Finish.
- **Or use a physical phone:** enable **Developer options** and **USB debugging**, then connect via USB.

---

## 2. Open the project in a terminal

- Open PowerShell (or Command Prompt).
- Go to the app folder:
  ```powershell
  cd C:\Users\jonko\Downloads\aria-auto-belay\aria-climb
  ```
  (Use your real path if it’s different.)

---

## 3. Install dependencies

```powershell
npm install --legacy-peer-deps
```

Wait for it to finish (can take a few minutes).

---

## 4. Firebase (required for login)

1. Go to **https://console.firebase.google.com** and sign in.
2. **Create a project** (or use an existing one). You can turn off Analytics for now.
3. **Add an Android app:**
   - Click the Android icon.
   - **Android package name:** `com.ariaclimb.app` (must match exactly).
   - Skip “App nickname” and “Debug signing certificate” for now. Register app.
4. **Download `google-services.json`** when Firebase offers it.
5. **Put the file in the app folder** so the path is:
   ```
   aria-climb\google-services.json
   ```
   Same folder as `app.json` and `package.json`.

---

## 5. Run the app on Android

**Start the emulator** (if using one): In Android Studio, **Device Manager** → click the **Play** button next to your device.

**Build and run:**

```powershell
npx expo run:android
```

- The **first run** will create the `android` folder and build the app (can take **5–15 minutes**).
- When the build finishes, the app should open on the emulator or your connected phone.

You should see the **Login** screen. You can sign up with email/password, then choose a role (e.g. Climber) to get into the app.

---

## If something fails

| Problem | What to do |
|--------|------------|
| `node` or `npm` not found | Install Node.js from https://nodejs.org (LTS). |
| `expo` or `npx` errors | From `aria-climb` run again: `npm install --legacy-peer-deps`. |
| No Android device/emulator | In Android Studio: SDK Manager → install SDK + tools; Device Manager → create and start an emulator. |
| Build fails (e.g. “SDK not found”) | In Android Studio, SDK Manager: set **Android SDK location** and install **Android SDK Command-line Tools**. |
| App crashes on open or “Firebase not configured” | Ensure `google-services.json` is in `aria-climb` and the package name in Firebase is `com.ariaclimb.app`. |
| “Unable to resolve module” or Metro errors | In `aria-climb`: `npx expo start --clear` then in another terminal `npx expo run:android`. |
| **“You need the Google services Gradle plugin”** | The project includes a plugin that adds it. Delete the `android` folder (if it exists), then run `npx expo run:android` again so the native project is regenerated. Or apply the manual Gradle fix below. |

### Manual Gradle fix (if the plugin isn’t applied)

If you still see the Google services Gradle plugin error after regenerating:

1. **Project-level** — Open `android/build.gradle.kts` (or `android/build.gradle`).  
   - **Kotlin:** In the `plugins { }` block add:  
     `id("com.google.gms.google-services") version "4.4.4" apply false`  
   - **Groovy:** In the `buildscript { dependencies { } }` block add:  
     `classpath 'com.google.gms:google-services:4.4.4'`

2. **App-level** — Open `android/app/build.gradle.kts` (or `android/app/build.gradle`).  
   - **Kotlin:** In the `plugins { }` block add:  
     `id("com.google.gms.google-services")`  
   - **Groovy:** At the bottom add:  
     `apply plugin: 'com.google.gms.google-services'`

3. Sync/rebuild: `npx expo run:android`.

---

## Quick recap

1. Node.js installed.  
2. Android Studio installed + SDK + one emulator (or USB phone).  
3. `cd aria-climb` → `npm install --legacy-peer-deps`.  
4. Firebase project → Android app `com.ariaclimb.app` → download `google-services.json` → put in `aria-climb`.  
5. Start emulator (or connect phone).  
6. `npx expo run:android`.  
7. Use the app (sign up → choose role → see Gym or Climber UI).
