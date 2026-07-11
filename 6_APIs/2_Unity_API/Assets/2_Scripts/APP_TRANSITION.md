# Deploying to Meta Quest 3 (Standalone Android Build)

This guide takes the eTactileKit Unity project from a **PC / Quest Link** setup to an **app that runs
directly on the Quest 3 headset** (Android standalone). On the headset the hardware is reached over
**WiFi with a fixed IP address** — serial (USB `COM`) is PC-only, and UDP auto-discovery is left
**off** so no extra Android permission or native code is needed.

> **Guiding principle:** the scene, haptics logic, patterns, calibration format and `HapticController`
> are **identical** on both targets. The **code already builds for both** — serial is auto-excluded on
> Android, the calibration loads correctly from inside the APK, and the kill switch is the same hand
> gesture everywhere. You only change **build settings** and point the manager at the kit's **IP**.
>
> The migration is **bidirectional**: this guide goes Windows → Android; switching back
> (Android → Windows / Quest Link) is covered in **§11** and also needs no code changes.

---

## 1. What changes at a glance

| Aspect | PC / Quest Link (today) | Quest 3 standalone (this guide) |
|---|---|---|
| Build target | Windows, Mono/IL2CPP | **Android, IL2CPP, ARM64** |
| Transport | Serial **or** WiFi | **WiFi only** (serial auto-excluded in code) |
| WiFi connection | Discovery **or** manual IP | **Manual IP** (discovery off - no extra permission) |
| Calibration load | from StreamingAssets | same file, read via `UnityWebRequest` on Android (built in) |
| Kill switch | **Hand gesture** (three-finger pinch) | **Same hand gesture** — one component, both modes |
| XR | Meta XR via Link | Meta XR **on-device** (Oculus/Meta plugin, ARM64) + hand tracking |
| Networking | any | **INTERNET permission** (added by *Internet Access = Require*) |
| Logs | Unity Console | `adb logcat` / Meta Quest Developer Hub |

Everything else — profiles, `PatternDB`, `HapticProfileProvider`, penetration detection, playback —
is untouched.

---

## 2. Prerequisites

- **Android Build Support** module installed in Unity Hub (✅ you have this) — includes the Android
  SDK, NDK and OpenJDK.
- **Meta XR All-in-One SDK** (`com.meta.xr.sdk.all`) already in the project (provides `OVRHand`, used
  by the kill switch, and the on-device runtime).
- A **Quest 3** in **Developer Mode** (enable in the *Meta Horizon* mobile app → *Devices* → your
  headset → *Developer Mode*; requires a verified developer org at developer.oculus.com).
- A USB-C cable, and optionally **Meta Quest Developer Hub (MQDH)** for install/log/streaming.
- The eTactileKit board reachable over WiFi at a **known IP** (same router in STA, or `192.168.4.1` in
  AP mode). Note the IP from the eTactileKitExplorer desktop app or your router's client list.

---

## 3. Part A — What the codebase already handles (no code edits)

These were built into the scripts so one codebase runs on both targets. Nothing to edit here:

- **Serial excluded on Android.** `SerialHandler.cs` and `ETactileKit.ConnectSerial` are wrapped in
  `#if UNITY_STANDALONE_WIN || UNITY_EDITOR`, and `ETactileKitManager.ConnectDevice` forces WiFi on
  non-desktop targets. The Android build never touches `System.IO.Ports`.
- **Calibration loads from inside the APK.** `ETactileKitManager` loads the StreamingAssets profile in
  a startup coroutine using `UnityWebRequest` on Android (and direct file I/O on desktop), so the same
  `template_32_electrode_calibration.json` works on device.
- **Unified kill switch.** `HapticKillSwitch.cs` (an `OVRHand` gesture) is the single emergency stop
  used on **both** PC/Link and the headset — there is no keyboard dependency anywhere.

The only scene step specific to the kill switch is wiring it up (also do this for the PC scene so both
behave identically):

1. Add a `HapticKillSwitch` component to a scene object (e.g. the manager's GameObject).
2. Assign **Manager**, and the **left/right `OVRHand`** components from your camera rig's hand anchors.
3. The gesture is **middle + ring + pinky pinched to the thumb** (index free), held ~1 s, on either
   hand — deliberate and effectively impossible to trigger by accident. `holdSeconds` is adjustable.

`OnDisable`/`OnApplicationQuit` also send OFF automatically as the safety net.

---

## 4. Part B — Unity project & build settings

### B1. Switch platform
`File ▸ Build Settings ▸ Android ▸ Switch Platform`. Add the open scene to *Scenes In Build*.

### B2. Run the Meta XR Project Setup Tool (does most of the work)
`Meta ▸ Tools ▸ Project Setup Tool` (a.k.a. *Oculus ▸ Tools*). Select the **Android** tab and **Apply
All** for *Required* and *Recommended* fixes. This sets Vulkan, Linear color space, IL2CPP/ARM64,
multithreaded rendering, correct min/target API, and more — saving you from setting them by hand.

### B3. XR Plug-in Management + hand tracking
`Project Settings ▸ XR Plug-in Management ▸ Android tab` → enable **Oculus** (Meta). Confirm your
scene has a working camera rig (the same `OVRCameraRig`/XR Origin you use over Link works on-device).
Because both the probes and the kill switch use hands, enable **Hand Tracking Support** on `OVRManager`
(*Quest Features* → Hand Tracking Support = *Controllers and Hands* or *Hands Only*). This also adds the
`com.oculus.permission.HAND_TRACKING` manifest entry automatically.

### B4. Player settings to verify (Project Settings ▸ Player ▸ Android)
- **Scripting Backend:** IL2CPP · **Target Architectures:** ARM64 only.
- **Api Compatibility Level:** `.NET Framework` (keep — required for `System.Net.Sockets`).
- **Minimum API Level:** Android 10 (API 29) or higher · **Target API Level:** as set by the Setup Tool.
- **Internet Access:** **Require** — this is what adds the `INTERNET` permission for TCP/UDP.
- **Package Name:** set a unique id, e.g. `com.yourorg.etactilekit`.
- **Active Input Handling:** `Both` (already set) works on device.

### B5. Configure the manager for WiFi-by-IP
Select the `ETactileKitManager` and set:
- **Connection Type = WiFi**
- **Use Discovery = OFF**
- **IP Address =** the board's address (STA: its fixed/known IP; AP: `192.168.4.1`)
- **Wifi Port = 8080**

That's the whole WiFi setup on device — no permission or native code beyond `INTERNET`. The code also
forces WiFi on Android as a safeguard if the field is left on Serial.

---

## 5. Part C — Android manifest / permissions

With **Internet Access = Require** (B4) Unity injects the only permission the app needs:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```
Hand tracking (B3) adds `com.oculus.permission.HAND_TRACKING` for you. Because discovery is off, **no
multicast permission and no native code are required**. You normally don't need to hand-write a
manifest at all.

---

## 6. Part D — Deploy to the headset

1. **Enable Developer Mode** (Part 2) and connect the Quest via USB-C. In the headset, **Allow USB
   debugging** when prompted (check *Always allow from this computer*).
2. Verify the device is seen: `adb devices` should list it (adb ships with the Android module, under
   the Unity Hub Android SDK `platform-tools`). MQDH also shows it.
3. **Build & Run** (`Ctrl+B`) to build the APK, install and launch in one step. Or **Build** an APK
   and install with `adb install -r yourapp.apk` / drag into MQDH / SideQuest.
4. **View logs:** `adb logcat -s Unity` (all our messages are prefixed `[eTactileKit]`), or use MQDH's
   log viewer. Tick **Development Build** in Build Settings for full logs and easier debugging.

---

## 7. Part E — Connecting to the kit from the headset

Both modes use a **fixed IP** on the manager (Use Discovery off):

- **STA (same router):** put the Quest and the kit on the **same WiFi / subnet**. Give the board a
  stable address (a DHCP reservation on the router, or a static IP in its firmware) and enter it as
  **IP Address**. Ensure the router doesn't isolate clients, and that the Quest (often 5 GHz) and the
  board (often 2.4 GHz) can reach each other.
- **AP mode:** in the Quest's *Settings ▸ WiFi*, join the board's `eTactileKit_<ID>` hotspot, then set
  **IP Address = 192.168.4.1**. The headset has no internet while on the AP, but the installed app runs
  fine.

The one-time setup sequence, calibration and patterns behave exactly as on PC once the TCP link is up.
(Auto-discovery still exists for the PC/Link build if you want it there; it is simply left off for the
headset build.)

---

## 8. Build & test checklist

1. Project compiles for Android with **no `System.IO.Ports` errors** (serial is auto-excluded).
2. Meta Project Setup Tool: all Required fixes applied; IL2CPP + ARM64; Internet Access = Require.
3. Oculus/Meta enabled under XR Plug-in Management (Android); **Hand Tracking Support** on.
4. Manager: **WiFi**, **Use Discovery off**, correct **IP Address**, port 8080.
5. `HapticKillSwitch` in the scene with Manager + both `OVRHand`s assigned.
6. `template_32_electrode_calibration.json` present in `Assets/StreamingAssets/`.
7. Developer Mode on; `adb devices` lists the Quest.
8. Build & Run installs and launches; `adb logcat -s Unity` shows `[eTactileKit] Setup complete …`.
9. Touch a haptic object with a probe → stimulation fires (same as over Link); the three-finger pinch
   stops it.

---

## 9. Troubleshooting

| Symptom | Check |
|---|---|
| Build error mentioning `System.IO.Ports` / `SerialPort` | Ensure the platform guards are intact — `SerialHandler.cs` is wrapped in `#if UNITY_STANDALONE_WIN \|\| UNITY_EDITOR` and `ConnectSerial` is guarded. Don't call serial from your own code on Android. |
| App runs but "Could not read default calibration" | Confirm `template_32_electrode_calibration.json` is in `Assets/StreamingAssets/` and the manager's **Default Calibration File Name** matches. |
| Connects to nothing on device | Verify **IP Address** is the board's current IP and the Quest is on the same subnet (or joined the AP). `Internet Access = Require` must be set. The WiFi connect times out in 5 s rather than hanging. |
| No haptics but link is up | Same layer/depth checks as the main README (probe on `Probe Layer`, object on `Interactable Layer`, depth ≥ threshold). Serial vs WiFi doesn't change this. |
| Kill gesture never fires | Hand Tracking Support enabled (B3)? `OVRHand`s assigned on `HapticKillSwitch`? Hands actually tracked (in view)? Try lowering `holdSeconds` while testing. |
| Black screen / not entering VR | XR Plug-in Management → Oculus not enabled for Android, or no camera rig in the scene. Re-run the Project Setup Tool. |
| `adb` device unauthorized | Re-plug and accept **Allow USB debugging** in the headset. |

---

## 10. Keeping both targets working

- The serial guards keep the desktop path (`UNITY_STANDALONE_WIN`/`EDITOR`) and the Android path
  separate from one codebase — never call serial unconditionally from your own scripts.
- Test in the **Editor over Quest Link** for fast iteration (serial *and* WiFi available there), then
  do a standalone **Build & Run** for on-device validation (WiFi-by-IP only).
- The calibration profile, `PatternDB`, providers, controller and the `HapticKillSwitch` gesture are
  shared verbatim — author, calibrate and wire once, run on both.

---

## 11. Reverse transition — Android → Windows (Quest Link / PC)

Taking a project that is currently set up for the headset **back** to a PC / Quest Link build needs
**no code changes** — the same `#if` guards re-enable the desktop paths automatically. It is just a
platform toggle plus the PC-side XR settings.

### What re-enables itself automatically (no edits)
- **Serial** compiles back in (`SerialHandler`, `ETactileKit.ConnectSerial`) — a `COM` port works again.
- **Calibration** is read with direct file I/O (the `#else` branch) instead of `UnityWebRequest`.
- The **WiFi-force guard** in `ConnectDevice` no longer applies, so `Connection Type` is honored as set
  (Serial *or* WiFi), and **UDP discovery** is available again.

### Steps
1. **Switch platform back:** `File ▸ Build Settings ▸ Windows, Mac, Linux` → Target Platform
   **Windows** → *Switch Platform*. (Unity re-imports assets; this can take a while.) For quick work
   you can also just press **Play** in the Editor over Quest Link without building.
2. **XR Plug-in Management ▸ Windows/Standalone tab** (separate from the Android tab): enable
   **Oculus** (or OpenXR + Meta) so Quest Link runs on the PC runtime. The Android tab settings don't
   affect the PC build.
3. **Player ▸ Windows settings:** keep **Api Compatibility Level = .NET Framework** (needed for serial
   *and* sockets). **Scripting Backend** can be **Mono** (fastest iteration) or IL2CPP — either is fine
   on PC.
4. **Manager transport:** choose **Serial** (set `Port Name` / `Baud Rate`) or **WiFi** (discovery or a
   manual IP). Everything else — patterns, calibration, and the `HapticKillSwitch` gesture — is
   unchanged.

### At a glance (reverse of §1)

| Aspect | Quest 3 standalone | PC / Quest Link |
|---|---|---|
| Build target | Android, IL2CPP, ARM64 | **Windows**, Mono or IL2CPP |
| Transport | WiFi only | **Serial and/or WiFi** (serial re-enabled) |
| WiFi connection | Manual IP | **Discovery or manual IP** |
| Calibration load | `UnityWebRequest` | **Direct file I/O** |
| XR provider tab | XR Plug-in Mgmt → **Android** | XR Plug-in Mgmt → **Windows/Standalone** |
| Kill switch | Hand gesture | **Same hand gesture** |

Because both directions share one scene and one codebase, you can bounce between them freely — build
for the headset, then switch back to Windows for Link-based debugging, with only the Build Settings
platform toggle in between.
