# eTactileKit Python API

Reference Python client for the **eTactileKit** electro-tactile hardware (Seeed XIAO
ESP32-S3). It speaks a compact binary protocol over **Serial** or **WiFi (TCP)** and is
the source of truth the Unity API mirrors.

- `api/etactilekit.py` – high-level device driver (electrode mapping, stim parameters,
  patterns, voltage read-back).
- `api/communication.py` – transports: `CommunicationSerial` and `CommunicationWiFi`.
- `api/discovery.py` – UDP broadcast discovery to find kits by unique ID (WiFi/STA).
- `test_serial.py`, `test_wifi.py` – runnable examples (arrow keys change amplitude, `q` quits).

## Requirements

```bash
pip install pyserial          # required for serial
# pip install zeroconf        # optional: only for the mDNS browsing snippet below
```

Python 3.8+. WiFi discovery uses only the standard library (`socket`).

---

## Connection modes at a glance

| Mode | How you address the board | Use when | Needs |
|---|---|---|---|
| **Serial (USB)** | `COMx` + baud `921600` | one board, wired, lowest latency | USB cable |
| **WiFi · discovery (STA)** | unique 6-hex **ID** (auto) | **workshops / many kits on one router** | shared router |
| **WiFi · mDNS (STA)** | `etactilekit-<ID>.local` | single board, Python/macOS convenience | mDNS on the LAN |
| **WiFi · AP fallback** | fixed IP `192.168.4.1` | no router / 1 PC ↔ 1 kit | join the kit's SSID |
| **WiFi · DHCP reservation** | a fixed IP you reserve | permanent lab setup | router admin access |

Every board derives a **unique ID** from its MAC at boot (e.g. `A1B2C3`). Once the kits are
on the network, list them all — IDs and current IPs — with the discovery script:

```bash
python -m api.discovery
# Found 2 board(s):
#   id=A1B2C3  ip=192.168.1.42:8080  mode=STA  name=etactilekit-A1B2C3
#   id=7F0C11  ip=192.168.1.57:8080  mode=STA  name=etactilekit-7F0C11
```

Write each board's ID on its label so you can pick it later. **With a single kit you don't even
need the ID** — `connect_by_discovery()` (the default `device_id=None`) just connects to the only
board found.

---

## 1. Serial (USB)

```python
from api.etactilekit import ETactileKit

etk = ETactileKit()
etk.connect_etactilekit_to_serial("COM12", 921600, timeout=0.005)  # Linux/macOS: "/dev/ttyACM0"
```

Run the example:

```bash
python test_serial.py        # edit PORT_1_NAME / BAUDRATE at the top first
```

> The ESP32-S3 USB-Serial-JTAG RX FIFO drops bytes if flooded; `CommunicationSerial`
> already paces writes in small chunks, so any payload size is safe.

## 2. WiFi — discovery (recommended for STA / multiple kits)

All kits join **one router** you control, then you find them by ID over UDP broadcast —
no need to know the DHCP-assigned IP, and it works even where mDNS does not.

```python
from api.etactilekit import ETactileKit

etk = ETactileKit()
etk.connect_by_discovery(device_id="A1B2C3")   # None = the only board found
```

List every kit in the room first (also runnable as `python -m api.discovery`):

```python
from api.discovery import discover_devices

for d in discover_devices(timeout=1.0):
    print(d)   # {'id': 'A1B2C3', 'name': 'etactilekit-A1B2C3', 'ip': '192.168.1.42', 'port': 8080, 'mode': 'STA'}
```

`test_wifi.py` uses this path by default — set `TARGET_DEVICE_ID` to pick a specific kit.

> Requirements: the PC and the kits must be on the **same subnet**, and the router must
> allow UDP broadcast between clients (disable "client isolation"/"AP isolation").

## 3. WiFi — mDNS (secondary, Python only)

Each board also advertises `etactilekit-<ID>.local` and the `_etactilekit._tcp` service
(TXT `id=<ID>`). On Windows/macOS you can connect straight to the hostname:

```python
etk.connect_etactilekit_to_wifi("etactilekit-A1B2C3.local", 8080, timeout=0.10)
```

Or browse all of them with `zeroconf` (`pip install zeroconf`):

```python
from zeroconf import Zeroconf, ServiceBrowser

class Listener:
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            ip = ".".join(map(str, info.addresses[0]))
            print(name, ip, info.properties.get(b"id"))

ServiceBrowser(Zeroconf(), "_etactilekit._tcp.local.", Listener())
```

> Note: **Unity/.NET cannot resolve `.local`** — that is why the UDP discovery above is
> the primary, cross-platform mechanism. Prefer it unless you are Python-only.

## 4. WiFi — AP fallback (no router)

If a board can't join the configured network it starts its own hotspot with a **unique
SSID** `eTactileKit_<ID>` (password `etactile@al`). Join that Wi-Fi, then:

```python
etk.connect_etactilekit_to_wifi("192.168.4.1", 8080, timeout=0.10)
```

One PC pairs with one kit this way (a PC can only join one AP at a time).

## 5. WiFi — DHCP reservation (deterministic, no discovery)

For a permanent setup, reserve a fixed IP per board on your router keyed by its MAC
(shown in the router's client list, or alongside the ID via `python -m api.discovery`). Then
just connect to that IP:

```python
etk.connect_etactilekit_to_wifi("192.168.1.50", 8080, timeout=0.10)
```

---

## After connecting (same for every mode)

```python
etk.set_electrode_mapping(list(range(32)))
etk.send_electrode_number(32)
etk.send_stimulation_mode(0)          # 0 monophasic, 1 biphasic
etk.send_stimulation_pulse_width(100) # µs
etk.send_stimulation_frequency(50)    # Hz
etk.send_channel_discharge_time(50)   # µs
print("sync:", etk.sync_check())      # echoes the configured electrode count
etk.send_stim_pattern([300] * 32)     # one 12-bit intensity (0–4095) per electrode
```

## Troubleshooting

| Symptom | Check |
|---|---|
| `discover_devices()` returns `[]` | PC and kits on the same router/subnet? Router blocking broadcast (client isolation)? Firewall blocking inbound UDP:8888? Did the board fall back to AP mode? (its `eTactileKit_<ID>` SSID would show in your Wi-Fi list). |
| "Multiple boards found" | Pass `device_id=` (or set `TARGET_DEVICE_ID`) with the kit's 6-hex code. |
| `.local` connects in Python but not Unity | Expected — use UDP discovery for Unity. |
| Can't connect in AP mode | Join the board's `eTactileKit_<ID>` Wi-Fi first; it's always `192.168.4.1`. |
| Serial: no device / garbled | Correct `COMx` and `921600` baud; not held by another app. |
