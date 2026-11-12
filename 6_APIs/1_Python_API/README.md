# eTactileKit Python API

Reference Python client for the **eTactileKit** electro-tactile hardware (Seeed XIAO
ESP32-S3). It speaks a compact binary protocol over **Serial** or **WiFi (TCP)** and is
the source of truth the Unity API mirrors.

- `api/etactilekit.py` – high-level device driver (connection, setup, electrode mapping,
  patterns, voltage read-back).
- `api/communication.py` – transports: `CommunicationSerial` and `CommunicationWiFi`.
- `api/discovery.py` – UDP broadcast discovery to find kits by unique ID (WiFi/STA).
- `test_etactilekit.py` – runnable example; set `MODE` (`"serial"` or `"wifi"`), `SERIAL_PORT` and
  `TARGET_DEVICE_ID` (your kit's ID, or `None`) at the top.
  **It stimulates:** the arrow keys raise and lower the amplitude of every electrode, `q` quits.

## Requirements

```bash
pip install pyserial          # required for serial
# pip install zeroconf        # optional: only for the mDNS browsing snippet below
```

Python 3.8+. WiFi discovery uses only the standard library (`socket`). Use an `ETactileKit` object
from one thread.

---

## Quick start

```python
from api.etactilekit import ETactileKit, StimulationMode

etk = ETactileKit()
etk.connect("serial")                        # the kit on USB (serial_port="COM13" picks a port)
# etk.connect("wifi", device_id="A1B2C3")    # WiFi, found by discovery
etk.configure(32, StimulationMode.MONOPHASIC, pulse_width=100, frequency=50)
etk.send_stim_pattern([300] * 32)            # one 12-bit intensity (0–4095) per electrode
etk.disconnect_etactilekit()
```

`connect(mode, ...)` takes `"serial"` or `"wifi"` and returns `True` only once the kit has answered
on that link (it also sets `etk.link`):

- **Serial:** with `serial_port=None` it uses the eTactileKit on USB (USB ID `303A:1001`). With
  several plugged in it refuses unless `device_id` picks one: the kit's USB serial number is its MAC,
  whose last three octets are its ID. A `serial_port` that holds a kit with another ID than
  `device_id` is refused too.
- **WiFi:** with `host=None` it finds the kit by UDP discovery (refusing when several answer and no
  `device_id` is given, or when the kit is busy). When no kit answers and no `device_id` is given, it
  tries the Access Point address `192.168.4.1`; a requested `device_id` is never replaced by whatever
  kit is at that address.

## How the kit picks a link

The firmware listens on USB serial and WiFi at the same time, and the first host to connect owns
the kit until it disconnects:

- **A serial host owns the kit** from the moment it opens the port until it closes it (or
  unplugs). The kit switches its WiFi radio off meanwhile, so it is not discoverable; WiFi comes
  back a few seconds after the port closes.
- **A WiFi host owns the kit** while its TCP connection is open. Other TCP clients are refused,
  discovery reports `busy=1`, and a serial host gets no answers. A client that vanishes without
  closing (out of range, crashed) is dropped after about 5 s, and one that leaves a reply unread
  for 0.25 s once its receive buffer is full is dropped too.
- **A refused serial host stays refused until it closes and reopens its port**, so it is never
  handed the kit halfway through a command stream.
- **Every connect and disconnect zeroes all amplitudes** (stimulation pattern and sense pulse
  height). The kit keeps every other setting — electrode number, mode, polarity, pulse widths,
  discharge time and frequency — so a new host inherits the previous host's until it sends its own.
- **The kit notices a closed serial port after 0.25 s.** A port reopened sooner continues the
  previous session, so `CommunicationSerial` waits 0.4 s after closing a port before it reopens
  it. A port another program has open is not retried: opened the moment that program released it,
  it would continue that program's session. The port is opened exclusively (also on Linux/macOS).
- **`connect()` adopts the electrode count the kit reports**, because the kit frames stimulation
  patterns by it. If it differs from the count you set earlier (the kit rebooted, or another host
  changed it), `connect()` warns and `send_stim_pattern()` refuses patterns until you run
  `configure()` again.
- **A failed write closes the link**, so the kit ends the session and zeroes every amplitude instead
  of continuing a half-sent command; reconnect to carry on.
- **The kit ends a session whose byte stream is out of step.** The protocol has no checksum, so an
  unknown command, a mode or polarity outside its range, a frequency of 0, a pulse height above 4095 or a payload
  that does not complete within 2 s means the bytes that follow could be read as anything. The kit
  zeroes every amplitude and drops the host: a TCP connection is closed, and a serial host's port
  stops working (the kit re-enumerates on USB). This API never sends such a stream; over WiFi, a
  frame that the network holds up half-way for more than 2 s ends the session the same way.
  Connect again to carry on.
- **`disconnect_etactilekit()` sends a zero pattern and sense pulse height 0 before it closes**, so
  nothing keeps running for the 0.25 s the kit takes to notice a closed serial port.

`CommunicationSerial` holds RTS and DTR low, so closing the port ends the session without
rebooting the board (the ESP32-S3 resets when it sees RTS high with DTR low).

## Connection modes at a glance

| Mode | How you address the board | Use when | Needs |
| --- | --- | --- | --- |
| **Serial (USB)** | `COMx` or the kit's ID (the baud rate is ignored) | one board, wired, lowest latency | USB cable |
| **WiFi · discovery (STA)** | unique 6-hex **ID** (auto) | **workshops / many kits on one router** | shared router |
| **WiFi · mDNS (STA)** | `etactilekit-<ID>.local` | single board, Python/macOS convenience | mDNS on the LAN |
| **WiFi · AP fallback** | fixed IP `192.168.4.1` | no router / 1 PC ↔ 1 kit | join the kit's SSID |
| **WiFi · DHCP reservation** | a fixed IP you reserve | permanent lab setup | router admin access |

Every board derives a **unique ID** — the last three octets of its MAC — at boot (e.g. `A1B2C3`),
so it also matches the tail of the MAC in your router's client list and of its USB serial number.
Once the kits are on the network, list them all — IDs and current IPs — with the discovery script:

```bash
python -m api.discovery
# Found 2 board(s):
#   id=A1B2C3  ip=192.168.1.42:8080  mode=STA  free  name=etactilekit-A1B2C3
#   id=7F0C11  ip=192.168.1.57:8080  mode=STA  busy  name=etactilekit-7F0C11
```

Write each board's ID on its label so you can pick it later. **With a single kit you don't even
need the ID** — `connect("wifi")` (the default `device_id=None`) just connects to the only
board found.

---

## 1. Serial (USB)

```python
from api.etactilekit import ETactileKit

etk = ETactileKit()
etk.connect("serial")                               # the kit on USB
# etk.connect("serial", device_id="A1B2C3")         # the kit with this ID, of several on USB
# etk.connect("serial", serial_port="COM13")        # a specific port (Linux/macOS: "/dev/ttyACM0")
```

Run the example:

```bash
python test_etactilekit.py   # MODE = "serial" at the top; TARGET_DEVICE_ID = your kit's ID or None
```

> Every command goes out in a single write. While the kit is busy, USB flow control holds the
> host back, so no byte is lost at any rate or payload size.

## 2. WiFi — discovery (recommended for STA / multiple kits)

All kits join **one router** you control, then you find them by ID over UDP broadcast —
no need to know the DHCP-assigned IP, and it works even where mDNS does not.

```python
from api.etactilekit import ETactileKit

etk = ETactileKit()
etk.connect("wifi", device_id="A1B2C3")   # None = the only board found
```

List every kit in the room first (also runnable as `python -m api.discovery`):

```python
from api.discovery import discover_devices

for d in discover_devices(timeout=1.0):
    print(d)   # {'id': 'A1B2C3', 'name': 'etactilekit-A1B2C3', 'ip': '192.168.1.42', 'port': 8080, 'mode': 'STA', 'busy': False, 'fw': '1.1'}
```

`discover_devices()` probes from every network interface and listens for `timeout` seconds in total,
re-sending the probe every 0.25 s. `busy` is `True` while another WiFi host owns the kit; `connect()`
reports that instead of trying. `test_etactilekit.py` uses this path with `MODE = "wifi"` — set
`TARGET_DEVICE_ID` to your kit's ID (or `None` for the only kit found).

> Requirements: the PC and the kits must be on the **same subnet**, and the router must
> allow UDP broadcast between clients (disable "client isolation"/"AP isolation").

> `CommunicationWiFi` leaves at least 4 ms between frames written back to back. The kit's TCP
> stack queues at most six incoming segments; faster bursts can stall the link for seconds (an OFF frame
> then waits too) or make the kit reset the connection, especially on a busy channel. Streams slower than
> 250 frames/s are not delayed.

## 3. WiFi — mDNS (secondary, Python only)

Each board also advertises `etactilekit-<ID>.local` and the `_etactilekit._tcp` service
(TXT `id=<ID>`). On Windows/macOS you can connect straight to the hostname:

```python
etk.connect("wifi", host="etactilekit-A1B2C3.local")
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

If a board can't join the configured network (at boot, or when a serial host lets go of it) it
starts its own hotspot with a **unique SSID** `eTactileKit_<ID>` (password `etactile@al`). A kit that
loses a router it had joined keeps rejoining it instead. Join that Wi-Fi, then:

```python
etk.connect("wifi", host="192.168.4.1")   # connect("wifi") also tries this address when no kit answers discovery
```

One PC pairs with one kit this way (a PC can only join one AP at a time).

## 5. WiFi — DHCP reservation (deterministic, no discovery)

For a permanent setup, reserve a fixed IP per board on your router keyed by its MAC
(shown in the router's client list; its last three octets are the kit's ID). Then
just connect to that IP:

```python
etk.connect("wifi", host="192.168.1.50")
```

---

## After connecting (same for every mode)

```python
from api.etactilekit import StimulationMode, StimulationPolarity

ok = etk.configure(32, StimulationMode.MONOPHASIC, pulse_width=100, frequency=50,
                   polarity=StimulationPolarity.ANODIC, discharge_time=50,
                   sense_pulse_height=0, sense_pulse_width=0,
                   electrode_mapping=None)   # None maps electrode i to hardware channel i
print("HV513 chips:", etk.hv513_num)
etk.send_stim_pattern([300] * 32)            # one 12-bit intensity (0–4095) per electrode
```

`configure()` sets every setting and verifies the result: the kit must report the new electrode
number, and the HV513 count is read (a warning if it gives fewer outputs, 8 per chip, than
electrodes). It returns `False`, with the reason printed, if the scan would not fit in the period
(nothing is sent), and, after disconnecting, if the link failed or the check did not match.
`send_stim_pattern()` sends nothing and returns `False` if the pattern or the electrode mapping does
not match the electrode count.

The individual `send_*` methods are also available (for example to change the frequency live). Each
returns `True` once sent and `False` if the link is not open or failed, or the setting was refused;
values outside the protocol's range raise `ValueError` (`TypeError` for non-integers).

## Safety limits

- **Scan time.** The kit pulses every electrode once per period, one after another. With a scan
  that does not fit in the period the kit scans back to back, below the frequency that was set,
  and it ends a scan after 260 ms, leaving out the electrodes it has not reached. The API keeps
  the kit away from both. It estimates a scan as
  `n × (phases × (max(pulse width, 10) + 8) + discharge time + 5) + 80` µs (phases = 2 for biphasic;
  the sense pulse width replaces the pulse width in Impedance Only mode) and refuses any setting
  that makes it exceed **80% of the period or 250 ms** (the message gives the highest frequency
  that would fit, when the scan is under 250 ms).
  For example 32 electrodes biphasic at 100 µs with 50 µs discharge take about 8.8 ms, so at most
  91 Hz; 128 electrodes take about 35 ms, so at most 23 Hz.
- **Setup order.** Each setting takes effect while the kit keeps scanning at its current (possibly
  a previous host's) period, so `configure()` sets the electrode number to 0 first and to its real
  value last. While the kit scans electrodes, a `send_*` call that changes the scan time is refused
  until this connection has sent every setting the scan time depends on; send electrode number 0
  first, or use `configure()`.
- **Amplitude.** Pattern values are 0–4095 of the 12-bit DAC. Start low and raise slowly.
- **Impedance Only mode** sends the sense pulse (height 0–255 of the DAC range, width in µs) to
  every electrode on every scan, in place of the pattern; a zero pattern does not stop it. Sense
  pulse height 0, another mode, or a disconnect does.

## Replies and timeouts

`sync_check()`, `get_voltage_readings()` and `update_and_get_hv513_count()` wait up to
`timeout` seconds for the kit's reply. Measured round trips are 0.1-0.5 ms over USB and a few ms over
WiFi (occasionally tens of ms), so the defaults are 0.1 s, and 1 s for the HV513 count, which waits
for the scan in progress and pauses stimulation while it senses. On a timeout they return an empty
list or `None`. The kit answers every request in order, so the bytes a timed-out reply still owes
are read and discarded before the next request; a reply still missing after 2 s means the link has
failed, and it is closed.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `discover_devices()` returns `[]` | PC and kits on the same router/subnet? Router blocking broadcast (client isolation)? Firewall blocking inbound UDP:8888? Did the board fall back to AP mode? (its `eTactileKit_<ID>` SSID would show in your Wi-Fi list). A kit connected over USB serial has its WiFi off. |
| "Multiple boards found" / "Several eTactileKits on USB" | Pass `device_id=` (or set `TARGET_DEVICE_ID`) with the kit's 6-hex code. |
| "Not sent: one scan of N electrodes would take about ..." | The settings would overrun the scan period; lower the frequency to the value given, or the electrode count, pulse width or discharge time. |
| "Not sent: ... has not set ... so the scan time cannot be checked" | Use `configure()`, or send electrode number 0 before changing timing settings one by one. |
| `.local` connects in Python but not Unity | Expected — use UDP discovery for Unity. |
| Can't connect in AP mode | Join the board's `eTactileKit_<ID>` Wi-Fi first; it's always `192.168.4.1`. |
| Serial: "could not open port ... in use" | Another program (a serial monitor, the desktop app, Unity) or another connection in this program has the port open; close it. |
| Serial: no device / "No eTactileKit found on USB" | Correct `COMx`; kit plugged in. A named `serial_port` that does not exist yet is retried for 2 s while the kit enumerates; with `serial_port=None` the kit must already be listed. |
| "COMx is eTactileKit X, not Y" / "eTactileKit Y is not on USB" | `device_id` (`TARGET_DEVICE_ID`) names another kit than the one on USB; set it to this kit's ID or `None`. |
| Serial port opens but `connect()` reports "no answer" | A WiFi host owns the kit. Disconnect it, then connect again (the port is reopened on every attempt). |
| Kit not discovered while it is plugged into USB | A program has its serial port open, so its WiFi is off. Close that program; WiFi returns within a few seconds. |
| "refused the connection" or discovery shows `busy` | Another WiFi host is connected to the kit. |
