# eTactileKit Unity API

This package integrates the **eTactileKit** electro-tactile hardware into Unity. It speaks the same
byte protocol as the reference Python API and gives you a small, clean set of components to:

- connect to the device (Serial or WiFi),
- load a per-electrode **calibration profile** (intensity + hardware mapping),
- define **tactile patterns** in code, and
- trigger those patterns from **collider penetration** in your scene.

There is intentionally **no UI** and **no hand rig** - just the API plus an example controller you can
drop onto any colliders (a tracked finger, a tool tip, etc.).

> Deploying to a **Quest 3 standalone build** (running on the headset, WiFi-only)? See
> [APP_TRANSITION.md](APP_TRANSITION.md) for the full Android/IL2CPP transition guide. This README
> covers the PC / Quest Link setup that both targets share.

---

## 1. Project setup (do this first)

1. **Api Compatibility Level** → `.NET Framework`
   `Project Settings ▸ Player ▸ Other Settings ▸ Configuration ▸ Api Compatibility Level`.
   Required for `System.IO.Ports` (serial) and `System.Net.Sockets` (WiFi).
2. **Active Input Handling** → `Both`
   `Project Settings ▸ Player ▸ Other Settings ▸ Active Input Handling`.
3. **Install the Meta XR All-in-One SDK** (`com.meta.xr.sdk.all`) via the Package Manager (Unity
   Registry / Git URL), plus any other plugins your headset needs. This provides the VR hands /
   controllers you will attach the probe colliders to.

> Serial note: on Windows the device typically enumerates as `COMx` (e.g. `COM12`) at `921600` baud.
>
> WiFi note: Unity connects by **IP address** or by **UDP discovery** (see §5). Unity/.NET has
> **no mDNS resolver**, so the board's `etactilekit-<ID>.local` hostname will **not** resolve here -
> use discovery (recommended) or a raw IP. Each board self-labels with a unique 6-hex `ID` (from its
> MAC); list every kit's ID and IP with the Python discovery script (`python -m api.discovery`), or
> read them from the Unity Console when the manager connects. With a single kit you need no ID at all.

---

## 2. How it fits together

```text
HapticController            (your scene)
  ├─ reads probe colliders, finds the deepest penetration each frame
  ├─ resolves the touched object's HapticProfile via HapticProfileProvider
  └─ plays the profile's pattern (frame timing + Once/Loop/Bounce)
        │
        ▼
ETactileKitManager         (connection + calibration + global params)
  └─ SendFrame(states): on-electrodes → calibrated intensity, off → 0
        │
        ▼
ETactileKit                (0_eTactileKitAPI: byte protocol port)
  └─ remaps to hardware channels, packs uint16 LE, writes one packet
        │
        ▼
Serial / WiFi handler  →  ESP32 hardware
```

| Concept | Script | Role |
|---|---|---|
| Device driver | `0_eTactileKitAPI/ETactileKit.cs` | Low-level protocol (no Unity types). |
| Transport | `SerialHandler.cs` / `WiFiHandler.cs` | Serial (chunked) / TCP I/O. |
| Discovery | `0_eTactileKitAPI/ETactileKitDiscovery.cs` | Find kits on the LAN by unique ID (UDP broadcast). |
| Manager | `1_Haptics/ETactileKitManager.cs` | Connection, global params, calibration, `SendFrame`. |
| Calibration | `CalibrationProfile.cs` | Per-electrode intensity + hardware mapping. |
| Patterns | `PatternDB.cs` | Code-defined `HapticPattern`s (frames + playback mode). |
| Profile asset | `HapticProfile.cs` | Which pattern + trigger depth for an object. |
| Provider | `HapticProfileProvider.cs` | Attaches a profile to an object. |
| Controller | `HapticController.cs` | Penetration → pattern playback. |

---

## 3. Calibration

Calibration stores **only** two things per electrode: the hardware **mapping** and the **intensity**
applied when that electrode is on. Everything else (pulse width, frequency, stim mode, …) is a global
parameter on the manager.

- **Generate a profile** with the **eTactileKitExplorer** desktop application, which exports the
  calibration JSON used here (per-electrode `mapping` + `intensity`).
- **Where it lives:** put the profile in `Assets/StreamingAssets/`. A sample is provided at
  `Assets/StreamingAssets/template_32_electrode_calibration.json` so it travels with the cloned repo.
- On the `ETactileKitManager`, set **Default Calibration File Name** to the file name inside
  `StreamingAssets` (default: `template_32_electrode_calibration.json`). It loads automatically on
  `Start` when no profile has been set in the inspector.
- In the manager inspector, **Calibration Profile** lets you **Import JSON** / **Export JSON** (the
  same format eTactileKitExplorer produces) and tune each electrode's **Intensity** directly.

### Global amplitude (gain)

The manager's **Amplitude Gain** slider scales **every** electrode's calibrated intensity as it is
sent, so you can adjust overall strength in one place while keeping the per-electrode balance from
calibration:

- Range **0 – 1.5**, default **1** (1 = use the calibration values exactly as they are).
- The scaled value is **rounded to the nearest integer** (the hardware only takes integers) and
  **clamped to the 12-bit DAC range** (0 – 4095), so a high calibration value with a gain above 1 can
  never overflow.
- It applies **live** - drag the slider while playing and the next frame uses it; no reconnect or
  re-calibration needed. It does not modify the calibration profile itself.
- From code: `manager.AmplitudeGain = 0.8f;` (clamped to the same range).

The manager runs this one-time setup on connect (mirrors the Python reference order):

```text
set mapping → electrode number → stim mode → polarity → pulse width →
sense pulse height → sense pulse width → channel discharge time → frequency →
read HV513 count → sync check
```

---

## 4. Creating a tactile pattern

Patterns are defined in code in `1_Haptics/PatternDB.cs`. A pattern is a list of **frames**; each
frame **lists the electrode ids that are ON** (value 1) plus an **on-time** and **off-time**
(milliseconds). When a frame is sent, each listed electrode is driven at its calibrated intensity and
all others are off. Listing active ids keeps patterns **independent of the electrode count** - that
count comes from the loaded calibration profile and is never hard-coded.

A pattern also has a **playback mode**:

- `Once` – play the frames one time, then stay silent until the probe re-enters.
- `Loop` – repeat frames `0..N-1` continuously while penetrated.
- `Bounce` – play frames forward then backward (ping-pong) while penetrated.

The two example patterns (`HorizontalScan`, `VerticalScan`) are authored by hand for the default
"Fingerpad TactDeform 32" layout - a 6×6 grid with the four corners removed:

```text
        col0  col1  col2  col3  col4  col5
 row0:    ·     0     1     2     3     ·
 row1:    4     5     6     7     8     9
 row2:   10    11    12    13    14    15
 row3:   16    17    18    19    20    21
 row4:   22    23    24    25    26    27
 row5:    ·    28    29    30    31     ·
```

`HorizontalScan` lights one **column** per frame (a vertical bar moving left→right); `VerticalScan`
lights one **row** per frame.

Patterns can be authored two ways:

- **Manual** – list the active ids per frame (`HorizontalScan`, `VerticalScan`). Best for spatial
  shapes tied to your electrode layout.
- **Programmatic** – build frames with a loop from the electrode count (`Blink`, `Buzz`). These take
  the active count so they work for any layout, and the result is cached:
  - `Blink` – all electrodes on for 200 ms, off for 200 ms, looping.
  - `Buzz` – one electrode per frame, 40 ms on / 0 ms off, scanning through all of them.

To add your own pattern:

1. Add a value to the `PatternId` enum.
2. Build a `HapticPattern` – either list the active ids per frame, or generate them in a loop (see
   `Blink` / `Buzz`).
3. Return it from `PatternDB.Get(id, electrodeCount)`.

If your hardware numbers electrodes differently, adjust the ids per frame to match. Ids outside the
active electrode range are ignored with a warning.

---

## 5. Example scene, step by step

1. **Manager** – create an empty GameObject, add `ETactileKitManager`.
   - **Serial:** choose `Serial` and set `Port Name` / `Baud Rate`.
   - **WiFi (recommended, STA):** choose `WiFi` and leave `Use Discovery` on. For a **single kit**,
     leave `Target Device Id` blank - it connects to the only board found. For **several kits**, set
     `Target Device Id` to the intended board's 6-hex code (from its label, the Unity Console log, or
     `python -m api.discovery`). The manager broadcasts on connect and resolves the kit's current IP
     automatically, so many kits can share one router. `Discovery Timeout Ms` sets how long it waits.
   - **WiFi (manual / AP fallback):** turn `Use Discovery` off (or when discovery finds nothing it
     falls back automatically) and set `IP Address` - a fixed/reserved IP, or `192.168.4.1` after
     joining a board's own `eTactileKit_<ID>` hotspot. `Wifi Port` is `8080`.
   - Set **Default Calibration File Name** to your profile in `StreamingAssets` (the sample
     `template_32_electrode_calibration.json` works out of the box), or **Import JSON** your own.
   - Leave the global stim params at their defaults (Biphasic, 100 µs, 50 Hz) unless you have reason
     to change them.
2. **Profile asset** – `Assets ▸ Create ▸ eTactileKit ▸ Haptic Profile`.
   - Pick a `Pattern Id` (e.g. `HorizontalScan`) and a `Min Penetration Depth Meters` (e.g. `0.002`).
3. **Touchable object** – on the object you want to feel:
   - add a `Collider`,
   - add `HapticProfileProvider` and assign the profile,
   - put the object on a dedicated layer (e.g. create an `Interactable` layer).
4. **Probe(s)** – add a `SphereCollider` to each finger tip / tool tip that should trigger haptics,
   and put them on a dedicated **probe layer** (e.g. create a `Probe` layer). No Rigidbody is
   required - penetration is computed directly, and probes are found automatically by layer.
5. **Controller** – add `HapticController` (anywhere):
   - assign `Manager`,
   - set `Probe Layer` to your probe layer,
   - set `Interactable Layer` to the touchable object's layer.
6. **Kill switch** – add a `HapticKillSwitch` component (e.g. on the manager's GameObject); assign
   `Manager` and your left/right `OVRHand`s. Emergency-stop gesture: middle + ring + pinky pinch held
   ~1 s (see §6).
7. **Play** – push a probe into the object past the threshold depth; the pattern plays at the
   calibrated intensity and stops when the probe withdraws.

> **Layers are the #1 cause of "nothing is detected".** The probe collider (finger/tool tip) and the
> touchable object must be on **two different layers**, and each must be selected on the controller:
> the finger's layer → `Probe Layer`, the object's layer → `Interactable Layer`. A finger left on the
> `Default` layer while `Probe Layer` points at a `Haptic Probe` layer will never be found - the
> controller logs a warning when it finds no probes. Use a dedicated probe layer (not `Default`) so
> unrelated colliders are not scanned. No Rigidbody is needed and the probe may be `Is Trigger`.
>
> Playback is **tied to the contacted collider**. While the same collider stays penetrated past the
> threshold the pattern keeps advancing - it is *not* replayed from the start each frame. A different
> object (or leaving and re-entering) starts the pattern over. A momentary loss of contact (physics
> jitter, depth chatter at the threshold) within `Reacquire Grace Seconds` (default 0.2 s) **resumes**
> at the current frame instead of restarting; set it to 0 to restart on any loss. Enable
> `Log State Changes` on the controller to watch start/resume/suspend transitions in the Console.
>
> Tip: enable **Run Connection Test** on the manager to pulse all electrodes on/off after connecting,
> as a quick hardware check (it ignores controller input while running).

---

## 6. Safety

- **Emergency stop = hand gesture.** Add a `HapticKillSwitch` component and assign the manager plus
  your `OVRHand`s. Holding an uncommon pose - **middle + ring + pinky pinched to the thumb** (index
  left free) for ~1 s on either hand - immediately sends OFF and disconnects. The same gesture works
  on PC / Quest Link and on the standalone headset (no keyboard needed).
- OFF is also sent automatically on disconnect, on `OnDisable`, and on application quit.
- **Amplitude Gain** above `1` drives every electrode *harder than calibrated* — raise it slowly and
  only if the calibrated level is too weak. `0` silences the output without disconnecting.

---

## 7. Building for the Quest 3 headset (standalone)

The same project also runs **directly on the Quest 3** (no PC). The code already builds for both
targets — serial is auto-excluded on Android, the calibration loads from inside the APK, and the
`HapticKillSwitch` gesture is identical — so this is mostly build settings. Full detail, deployment
and troubleshooting are in [APP_TRANSITION.md](APP_TRANSITION.md); the essentials:

1. **Install Android Build Support** (Unity Hub), then `File ▸ Build Settings ▸ Android ▸ Switch
   Platform`.
2. **Run the Meta XR Project Setup Tool** (`Meta ▸ Tools ▸ Project Setup Tool`, Android tab → *Apply
   All*) — it sets IL2CPP, ARM64, Vulkan, API levels, etc.
3. **XR Plug-in Management ▸ Android** → enable **Oculus**; enable **Hand Tracking Support** on
   `OVRManager` (needed for the probes and the kill switch).
4. **Player ▸ Android:** Scripting Backend **IL2CPP**, Target Architecture **ARM64**, Api Compatibility
   **.NET Framework**, **Internet Access = Require** (adds the `INTERNET` permission), unique Package Name.
5. **Manager:** Connection Type **WiFi**, **Use Discovery off**, **IP Address** = the kit's IP (STA: a
   reserved/static IP; AP: `192.168.4.1`), port `8080`.
6. **Deploy:** enable Developer Mode on the Quest, connect USB-C, allow USB debugging, then **Build &
   Run** (`Ctrl+B`). View logs with `adb logcat -s Unity`.

On the headset the kit is reached over **WiFi only** (serial is desktop-only); everything else —
patterns, calibration, penetration → haptics — behaves exactly as over Quest Link.

To switch a headset-configured project **back to PC / Quest Link**, see
[APP_TRANSITION.md §11 (Android → Windows)](APP_TRANSITION.md) — it's a platform toggle with **no code
changes** (serial, file-based calibration and discovery re-enable themselves automatically).

---

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| No collisions detected at all | Finger/tool collider's Layer must match the controller's `Probe Layer` (a `Default`-layer finger with a different `Probe Layer` is never found - watch for the "found no probe colliders" warning). Object's Layer must be in `Interactable Layer`, and the two must differ. |
| Detected but no stimulation | Penetration ≥ profile `Min Penetration Depth Meters`? Profile `Enable Haptics` on? Probe actually overlapping (not just touching) the object? Device connected and not in Run Connection Test? **Amplitude Gain** not 0? |
| Stimulation too weak / too strong | Adjust the manager's **Amplitude Gain** (0–1.5, default 1) — it scales all calibrated intensities live. If only *some* electrodes feel wrong, the per-electrode balance is off: re-calibrate in eTactileKitExplorer, or tune individual **Intensity** values in the manager's calibration list. |
| "Cannot connect without a valid calibration profile" | Assign / import a valid profile (mapping must be a permutation of `0..count-1`). |
| WiFi: "No kits discovered" | PC and kits on the same router/subnet? Router allowing UDP broadcast (disable client/AP isolation)? Windows Firewall allowing Unity inbound UDP:8888? Did the board fall back to AP mode? (its `eTactileKit_<ID>` SSID would show in your Wi-Fi list). Manager falls back to `IP Address` when nothing answers. |
| WiFi: connected to the wrong kit | Set `Target Device Id` to the intended board's 6-hex code (blank = first found). |
| WiFi: `*.local` never connects | Expected - Unity/.NET can't resolve mDNS; use `Use Discovery` or a raw IP. |
| Wrong / missing port | Correct `COMx` and `921600` baud; device plugged in; not held by another app. |
| "Electrode id N is out of range" warning | A pattern frame lists an id ≥ the calibration's electrode count; fix the ids in `PatternDB.cs`. |
| Garbled serial data | Confirm Api Compatibility Level is `.NET Framework`. |
