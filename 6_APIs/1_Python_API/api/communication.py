#-------------------------------------------------------------------------------
# Serial Communication Class
#-------------------------------------------------------------------------------
import errno
import os
import re
import socket
import string
import struct
import time

import serial
import serial.tools.list_ports

try:
    import termios  # tcflush on a vanished POSIX port raises termios.error, not SerialException
    _PORT_ERRORS = (serial.SerialException, OSError, termios.error)
except ImportError:
    _PORT_ERRORS = (serial.SerialException, OSError)

# USB IDs of the ESP32-S3 USB Serial/JTAG port the kit enumerates as.
ETACTILEKIT_USB_VID = 0x303A
ETACTILEKIT_USB_PID = 0x1001

# The kit ends a serial session once the port has been closed for 250 ms (SERIAL_LINK_TIMEOUT_MS in
# the firmware); a port reopened sooner continues the previous session (amplitudes and any half-sent
# command included). Reopening only after this gap lets the kit zero the amplitudes and restart its
# parser first.
SERIAL_REOPEN_GAP_S = 0.4
_OPEN = None      # _last_close value of a port opened by this process and not closed through disconnect()
_last_close = {}  # port key -> time.monotonic() of this process's last close of that port, or _OPEN


def _port_key(port_name):
    """Key for a port name. Windows names are case-insensitive and may carry the device-namespace prefix."""
    if os.name != "nt":
        return port_name
    name = port_name.upper()
    return name[4:] if name.startswith("\\\\.\\") else name


def _natural_key(port_name):
    """Sort key that puts COM9 before COM10."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", port_name)]


def _kit_id(serial_number):
    """The 6-hex kit ID behind a USB serial number. The kit reports its MAC (e.g. 98:3D:AE:60:4F:E0);
    the ID is the MAC's last three octets."""
    digits = "".join(c for c in (serial_number or "") if c in string.hexdigits).upper()
    return digits[-6:] if len(digits) == 12 else None


def _kit_ports():
    return [p for p in serial.tools.list_ports.comports()
            if p.vid == ETACTILEKIT_USB_VID and p.pid == ETACTILEKIT_USB_PID]


def find_serial_ports(device_id=None):
    """Serial ports of the eTactileKit boards plugged into this computer, in port order. With device_id,
    only the port of the kit with that 6-hex ID (matched through its USB serial number)."""
    ports = _kit_ports()
    if device_id is not None:
        ports = [p for p in ports if _kit_id(p.serial_number) == device_id.upper()]
    return sorted((p.device for p in ports), key=_natural_key)


def serial_port_kit_id(port_name):
    """The 6-hex ID of the eTactileKit on port_name, or None if no eTactileKit is listed on it."""
    key = _port_key(port_name)
    for p in _kit_ports():
        if _port_key(p.device) == key:
            return _kit_id(p.serial_number)
    return None


def _port_missing(error):
    """True if a port could not be opened because it does not exist (yet)."""
    return getattr(error, "errno", None) == errno.ENOENT or "FileNotFoundError" in str(error)


class CommunicationSerial:
    """Manages serial communication with the eTactileKit ESP32. Use it from one thread. The port is opened
    exclusively; on Linux/macOS that is an advisory lock, so a program that opens the port without locking it
    (e.g. screen or cat) is not kept out.

    The kit holds the host off with USB flow control while it is busy, so each frame goes out in a
    single write and no byte is dropped. Reads poll with a short fixed port timeout until their own
    deadline, so the port is never reconfigured per call."""
    _READ_POLL_S = 0.01      # Port timeout of each read attempt inside a read's deadline
    _WRITE_TIMEOUT_S = 1.0   # A write the kit has not taken by then means the link has stalled

    def __init__(self, port_name, baudrate, timeout=0.02):
        self.port_name = port_name
        self.baudrate = baudrate
        self.timeout = timeout   # Default read deadline in seconds
        self.serial_port = None
        self.connected = False

    def connect(self, open_timeout=2.0):
        """
        Opens the serial port exclusively. A port that does not exist yet (the board is still
        enumerating after being plugged in or rebooting) is retried for up to open_timeout seconds.

        Returns:
            bool: True if the port was opened.
        """
        key = _port_key(self.port_name)
        if key in _last_close:
            # Opened before by this process; if it was not closed through disconnect() (e.g. the object
            # was garbage-collected), when it closed is unknown, so wait the whole gap.
            closed = _last_close[key]
            wait = SERIAL_REOPEN_GAP_S - (0 if closed is _OPEN else time.monotonic() - closed)
            if wait > 0:
                time.sleep(wait)
        deadline = time.monotonic() + open_timeout
        while True:
            try:
                self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=self._READ_POLL_S,
                                                 write_timeout=self._WRITE_TIMEOUT_S, exclusive=True)
                break
            except _PORT_ERRORS as e:
                # Only a port that does not exist yet is retried: it appears once the kit has enumerated,
                # with a new session. A port another program holds is not; opened the moment it is
                # released, it would continue that program's session, amplitudes included.
                if not _port_missing(e) or time.monotonic() >= deadline:
                    hint = ("" if _port_missing(e) else
                            " The port is in use by another program (e.g. a serial monitor, the desktop app or "
                            "Unity) or by another connection in this program.")
                    print(f"Could not open {self.port_name}: {e}.{hint}")
                    return False
                time.sleep(0.1)
        # The ESP32-S3 USB-Serial-JTAG resets the chip while RTS is high and DTR is low, which
        # the host produces when it drops the lines on close. Lowering RTS first, then DTR,
        # never passes through that state, so closing the port ends the session without a reboot.
        _last_close[key] = _OPEN
        self.connected = True
        try:
            self.serial_port.rts = False
            self.serial_port.dtr = False
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
        except _PORT_ERRORS as e:
            print(f"Serial error on {self.port_name}: {e}")
            self.disconnect()
            return False
        return True

    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except _PORT_ERRORS:
                pass
            _last_close[_port_key(self.port_name)] = time.monotonic()
        self.serial_port = None
        self.connected = False
        print("Serial port disconnected")

    def _read_exact(self, num_bytes, timeout):
        """Reads up to num_bytes, returning early once all have arrived or the timeout has passed."""
        data = bytearray()
        deadline = time.monotonic() + timeout
        if not self.connected:
            return b""
        try:
            while len(data) < num_bytes:
                data += self.serial_port.read(num_bytes - len(data))
                if time.monotonic() >= deadline:
                    break
        except _PORT_ERRORS as e:
            print(f"Serial error: {e}")
            self.disconnect()
        return bytes(data)

    def read_raw_bytes(self, num_bytes, timeout=None):
        """Read exactly num_bytes and return raw bytes (shorter on timeout). None uses the default timeout."""
        return self._read_exact(num_bytes, self.timeout if timeout is None else timeout)

    def read_bytes_with_timeout(self, num_bytes=1, byteorder='little', timeout=0.010):
        """
        Read exactly num_bytes within the given timeout.

        Returns:
            int: The received value, or 0 on timeout.
        """
        raw = self._read_exact(num_bytes, timeout)
        if len(raw) < num_bytes:
            return 0
        return int.from_bytes(raw, byteorder=byteorder)

    def read_bytes(self, num_bytes=1, byteorder='little'):
        raw = self._read_exact(num_bytes, self.timeout)
        return int.from_bytes(raw, byteorder=byteorder)

    def write_bytes(self, val, num_bytes=1, byteorder='little'):
        """Send val as num_bytes in one frame. Returns True if it was written."""
        return self.write_byte_array(int.to_bytes(val, num_bytes, byteorder))

    def write_byte_array(self, data):
        """
        Send a frame in a single write; the kit's USB flow control paces it. If the write fails or is
        cut short, the port is closed: the kit then ends the session and zeroes every amplitude
        instead of continuing a half-sent frame.

        Returns:
            bool: True if the whole frame was written.
        """
        if not self.connected:
            return False
        try:
            if self.serial_port.write(data) == len(data):
                return True
            print("Serial write was cut short.")
        except serial.SerialTimeoutException:
            print(f"Serial write timed out after {self._WRITE_TIMEOUT_S} s: the kit is not reading.")
        except _PORT_ERRORS as e:
            print(f"Serial error on send: {e}")
        self.disconnect()
        return False

    def clear_input_buffer(self):
        if not self.connected:
            return
        try:
            self.serial_port.reset_input_buffer()
        except _PORT_ERRORS as e:
            print(f"Serial error: {e}")
            self.disconnect()

    def clear_output_buffer(self):
        if not self.connected:
            return
        try:
            self.serial_port.reset_output_buffer()
        except _PORT_ERRORS as e:
            print(f"Serial error: {e}")
            self.disconnect()


#-------------------------------------------------------------------------------
# WiFi Communication Class
#-------------------------------------------------------------------------------
# SO_LINGER on, 0 s: closing then resets the connection and discards unsent data.
_LINGER_ABORT = struct.pack("HH", 1, 0) if os.name == "nt" else struct.pack("ii", 1, 0)


class CommunicationWiFi:
    """Manages TCP/IP communication with the eTactileKit ESP32. Use it from one thread."""
    _WRITE_TIMEOUT_S = 1.0   # A frame the kit's TCP stack has not taken by then means the link has stalled
    # The kit's TCP stack queues at most six received segments and refuses more until a timer retries
    # them, which stalls the link for 0.2-0.5 s. Frames written less than this far apart (each one
    # leaves as its own segment) are spaced out so the kit drains them; slower streams are not delayed.
    # Bursts of 200 frames stalled the link for seconds, or made the kit reset the connection, in 3 of 36
    # trials at 2 ms spacing on a busy channel, and in none of 32 at 4 ms or more.
    _MIN_FRAME_GAP_S = 0.004

    def __init__(self, ip, port, timeout=0.02):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.connected = False
        self._last_write = 0.0

    def connect(self, connect_timeout=5.0):
        """
        Opens a TCP connection to the ESP32.

        Returns:
            bool: True if the connection succeeds, False otherwise.
        """
        sock = None
        try:
            print(f"Connecting to {self.ip}:{self.port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(connect_timeout)
            sock.connect((self.ip, self.port))
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(self.timeout)
            self.sock = sock
            self.connected = True
            return True
        except Exception as e:
            if isinstance(e, ConnectionRefusedError):
                # The kit only listens while no host owns it.
                print(f"{self.ip}:{self.port} refused the connection: the kit is in use by another host.")
            elif isinstance(e, socket.timeout):
                print(f"Connecting to {self.ip}:{self.port} timed out. Check the address and that the kit is "
                      "reachable; a kit connected to a USB serial host has its WiFi switched off.")
            else:
                print(f"Connection failed: {e}")
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
            self.connected = False
            return False

    def disconnect(self, abort=False):
        """Close the connection. With abort, reset it instead, so frames still waiting in the send buffer
        are discarded and the kit ends the session at once instead of running them first."""
        if self.sock:
            try:
                if abort:
                    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, _LINGER_ABORT)
            except OSError:
                pass
            finally:
                try:
                    self.sock.close()
                except OSError:
                    pass
            self.sock = None
        self.connected = False
        print("WiFi disconnected")

    def _recv_exact(self, num_bytes, timeout):
        """
        Reads exactly num_bytes from the socket within the given timeout.

        TCP recv() may return fewer bytes than requested. This method
        accumulates chunks until the full count arrives or time runs out.
        A connection the kit closed, or one that failed, is closed.

        Returns:
            bytes: The received data (may be shorter than num_bytes on timeout).
        """
        data = bytearray()
        if not self.connected or self.sock is None:
            return b""
        deadline = time.monotonic() + timeout
        try:
            while len(data) < num_bytes:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self.sock.settimeout(max(remaining, 0.001))
                try:
                    chunk = self.sock.recv(num_bytes - len(data))
                except (socket.timeout, TimeoutError):
                    break
                if not chunk:
                    print(f"The kit at {self.ip}:{self.port} closed the connection.")
                    self.disconnect()
                    break
                data.extend(chunk)
        except OSError as e:
            print(f"Socket error: {e}")
            self.disconnect()
        if self.sock is not None:
            self.sock.settimeout(self.timeout)
        return bytes(data)

    def read_raw_bytes(self, num_bytes, timeout=None):
        """Read exactly num_bytes and return raw bytes (shorter on timeout). None uses the default timeout."""
        return self._recv_exact(num_bytes, self.timeout if timeout is None else timeout)

    def read_bytes_with_timeout(self, num_bytes=1, byteorder='little', timeout=0.010):
        """
        Read exactly num_bytes within the given timeout.

        Returns:
            int: The received value, or 0 on timeout/error.
        """
        raw = self._recv_exact(num_bytes, timeout)
        if len(raw) < num_bytes:
            return 0
        return int.from_bytes(raw, byteorder=byteorder)

    def read_bytes(self, num_bytes=1, byteorder='little'):
        """
        Read exactly num_bytes using the default timeout.

        Returns:
            int: The received value.
        """
        raw = self._recv_exact(num_bytes, self.timeout)
        return int.from_bytes(raw, byteorder=byteorder)

    def write_bytes(self, val, num_bytes=1, byteorder='little'):
        """Send val as num_bytes in one frame. Returns True if it was sent."""
        return self.write_byte_array(int.to_bytes(val, num_bytes, byteorder))

    def write_byte_array(self, data):
        """
        Send a pre-built bytes/bytearray in a single sendall call. If the send fails, the connection is
        reset: the kit then ends the session and zeroes every amplitude.

        Returns:
            bool: True if the whole frame was sent.
        """
        if not self.connected or self.sock is None:
            return False
        wait = self._last_write + self._MIN_FRAME_GAP_S - time.perf_counter()
        if wait > 0:
            time.sleep(wait)
        try:
            self.sock.settimeout(self._WRITE_TIMEOUT_S)
            self.sock.sendall(data)
            self.sock.settimeout(self.timeout)
            self._last_write = time.perf_counter()
            return True
        except OSError as e:
            print(f"Socket error on send: {e}")
            self.disconnect(abort=True)
            return False

    def clear_input_buffer(self):
        """Drain any pending bytes from the socket receive buffer. A connection the kit closed, or one that
        failed, is closed."""
        if not self.connected or self.sock is None:
            return
        self.sock.settimeout(0)
        try:
            while True:
                if not self.sock.recv(4096):
                    print(f"The kit at {self.ip}:{self.port} closed the connection.")
                    self.disconnect()
                    return
        except (BlockingIOError, socket.timeout):
            pass
        except OSError as e:
            print(f"Socket error: {e}")
            self.disconnect()
            return
        self.sock.settimeout(self.timeout)
