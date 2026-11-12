#-------------------------------------------------------------------------------
# UDP broadcast discovery for eTactileKit boards
#
# In station (STA) mode every board joins the same router and self-labels with a
# unique 6-hex ID derived from its MAC. It advertises as etactilekit-<ID>.local and
# also answers a tiny UDP broadcast probe with its ID + current IP. This module uses
# that probe so Python (and, with the same protocol, Unity) can find kits by ID
# without depending on mDNS/.local resolution.
#
# Protocol (must match the firmware: port, probe and prefix in configuration.h, reply
# fields in lib/Communication/communication.cpp):
#   request : the 4 bytes b"ETK?" broadcast to <broadcast>:DISCOVERY_PORT
#   reply   : "ETK!;id=A1B2C3;name=etactilekit-A1B2C3;ip=192.168.1.42;port=8080;mode=STA;busy=0;fw=1.1"
#             busy=1 means another WiFi host owns the kit. A kit connected over USB serial
#             has its WiFi switched off and does not answer at all.
#-------------------------------------------------------------------------------
import select
import socket
import time

# Must match the firmware defines in configuration.h.
DISCOVERY_PORT   = 8888
DISCOVERY_PROBE  = b"ETK?"
DISCOVERY_PREFIX = "ETK!"
DEFAULT_TCP_PORT = 8080   # Control port of a reply that does not name one
PROBE_INTERVAL_S = 0.25   # The probe is re-sent this often within the listen window (UDP is lossy)


def _local_ipv4_addresses():
    """Best-effort set of this host's IPv4 addresses so discovery also works on
    machines with several interfaces (Wi-Fi + Ethernet + VPN). An empty string in
    the result means 'let the OS pick the default interface'."""
    addrs = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addrs.add(info[4][0])
    except socket.gaierror:
        pass
    # Also the address the OS would use to reach the internet (no packet is sent).
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        addrs.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    addrs.discard("127.0.0.1")
    return addrs or {""}


def _parse_reply(text, src_ip):
    """Parse an 'ETK!;id=..;ip=..;port=..;mode=..' reply into a dict, or None if the
    datagram is not a valid eTactileKit reply."""
    if not text.startswith(DISCOVERY_PREFIX):
        return None
    device = {"id": None, "name": None, "ip": src_ip, "port": DEFAULT_TCP_PORT, "mode": None}
    for token in text.split(";")[1:]:
        key, sep, value = token.partition("=")
        if sep:
            device[key.strip()] = value.strip()   # unknown keys are kept, ignored downstream
    try:
        device["port"] = int(device["port"])
    except (TypeError, ValueError):
        device["port"] = DEFAULT_TCP_PORT
    device["busy"] = device.get("busy") == "1"
    return device if device.get("id") else None


def discover_devices(timeout=1.0, port=DISCOVERY_PORT):
    """
    Broadcast a discovery probe from every local IPv4 interface and collect replies from every
    eTactileKit on the LAN. Listens for `timeout` seconds in total, re-sending the probe every
    PROBE_INTERVAL_S.

    Args:
        timeout:  seconds to listen for replies.
        port:     UDP discovery port (must match the firmware).

    Returns:
        list[dict], one per board, deduplicated by ID and sorted by ID, e.g.
            {'id': 'A1B2C3', 'name': 'etactilekit-A1B2C3',
             'ip': '192.168.1.42', 'port': 8080, 'mode': 'STA', 'busy': False}
        Empty list if none answered.
    """
    sockets = []
    for local_ip in _local_ipv4_addresses():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((local_ip, 0))   # send out of this specific interface ("" = the OS's choice)
            sock.setblocking(False)
            sockets.append(sock)
        except OSError:
            sock.close()

    found = {}
    deadline = time.monotonic() + timeout
    next_probe = 0.0
    try:
        while sockets:
            now = time.monotonic()
            if now >= deadline:
                break
            if now >= next_probe:
                for sock in sockets:
                    try:
                        sock.sendto(DISCOVERY_PROBE, ("255.255.255.255", port))
                    except OSError:
                        pass
                next_probe = now + PROBE_INTERVAL_S
            try:
                readable, _, _ = select.select(sockets, [], [], max(0.0, min(deadline, next_probe) - now))
            except OSError:
                break
            for sock in readable:
                try:
                    data, addr = sock.recvfrom(512)
                except OSError:
                    continue
                device = _parse_reply(data.decode("ascii", "ignore"), addr[0])
                if device:
                    found[device["id"]] = device   # dedup by unique id
    finally:
        for sock in sockets:
            sock.close()
    return sorted(found.values(), key=lambda d: d["id"])


if __name__ == "__main__":
    devices = discover_devices()
    if not devices:
        print("No eTactileKit boards found. Check they share the same router/subnet.")
    else:
        print(f"Found {len(devices)} board(s):")
        for d in devices:
            state = "busy" if d["busy"] else "free"
            print(f"  id={d['id']}  ip={d['ip']}:{d['port']}  mode={d['mode']}  {state}  name={d['name']}")
