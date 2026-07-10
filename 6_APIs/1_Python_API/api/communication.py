#-------------------------------------------------------------------------------
# Serial Communication Class
#-------------------------------------------------------------------------------
import serial
import time

class CommunicationSerial:
    """Manages serial communication with the eTactileKit ESP32."""
    # The ESP32-S3 USB-Serial-JTAG RX ISR drops bytes when its 64-byte hardware FIFO is not
    # serviced quickly enough - which happens when bytes arrive faster than the firmware reads
    # them Sending in small chunks with a brief gap keeps the FIFO from overflowing,
    # so every command lands intact.
    _SERIAL_CHUNK = 8       # max bytes per USB write
    _SERIAL_GAP_S = 0.003   # pause after each chunk (also spaces consecutive commands)

    def __init__(self, port_name, baudrate, timeout=0.02):
        self.port_name = port_name
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None
        self.connected = False

    def connect(self):
        """
        Continuously attempts to open the serial port until successful.

        Returns:
            bool: True once the connection is established.
        """
        prev = time.time()
        while not self.connected:
            try:
                self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=self.timeout)
                self.connected = True
                print(f"Connected to serial device at {self.port_name} ({self.baudrate} baud)")
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                return True
            except Exception:
                if time.time() - prev > 2:
                    print("No serial device detected. Check connections.")
                    prev = time.time()
        return True

    def disconnect(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.serial_port = None
        self.connected = False
        print("Serial port disconnected")

    def read_raw_bytes(self, num_bytes, timeout=None):
        """Read exactly num_bytes and return raw bytes (no integer conversion)."""
        if timeout is not None:
            self.serial_port.timeout = timeout
        raw = self.serial_port.read(num_bytes)
        if timeout is not None:
            self.serial_port.timeout = self.timeout
        return raw

    def read_bytes_with_timeout(self, num_bytes=1, byteorder='little', timeout=0.010):
        self.serial_port.timeout = timeout
        raw = self.serial_port.read(num_bytes)
        self.serial_port.timeout = self.timeout
        return int.from_bytes(raw, byteorder=byteorder)

    def read_bytes(self, num_bytes=1, byteorder='little'):
        raw = self.serial_port.read(num_bytes)
        return int.from_bytes(raw, byteorder=byteorder)

    def read_string(self):
        return self.serial_port.readline().decode('utf-8').strip()

    def write_bytes(self, val, num_bytes=1, byteorder='little'):
        self.serial_port.write(int.to_bytes(val, num_bytes, byteorder))
        return True

    def write_byte_array(self, data):
        """Send bytes in small paced chunks so the ESP32-S3 USB-Serial-JTAG RX FIFO never
        overflows (see _SERIAL_CHUNK / _SERIAL_GAP_S). Safe for any payload size."""
        for i in range(0, len(data), self._SERIAL_CHUNK):
            self.serial_port.write(data[i:i + self._SERIAL_CHUNK])
            time.sleep(self._SERIAL_GAP_S)

    def clear_input_buffer(self):
        self.serial_port.reset_input_buffer()

    def clear_output_buffer(self):
        self.serial_port.reset_output_buffer()


#-------------------------------------------------------------------------------
# WiFi Communication Class
#-------------------------------------------------------------------------------
import socket
import time

class CommunicationWiFi:
    """Manages TCP/IP communication with the eTactileKit ESP32."""

    def __init__(self, ip, port, timeout=0.02):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.connected = False

    def connect(self):
        """
        Opens a TCP connection to the ESP32.

        Returns:
            bool: True if the connection succeeds, False otherwise.
        """
        sock = None
        try:
            print(f"Connecting to {self.ip}:{self.port}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.ip, self.port))
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(self.timeout)
            self.sock = sock
            self.connected = True
            print(f"Connected to {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass
            self.connected = False
            return False

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.connected = False
        print("WiFi disconnected")

    def _recv_exact(self, num_bytes, timeout):
        """
        Reads exactly num_bytes from the socket within the given timeout.

        TCP recv() may return fewer bytes than requested. This method
        accumulates chunks until the full count arrives or time runs out.

        Returns:
            bytes: The received data (may be shorter than num_bytes on timeout).
        """
        data = bytearray()
        deadline = time.monotonic() + timeout
        while len(data) < num_bytes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self.sock.settimeout(max(remaining, 0.001))
            try:
                chunk = self.sock.recv(num_bytes - len(data))
                if not chunk:
                    self.connected = False
                    break
                data.extend(chunk)
            except (socket.timeout, TimeoutError):
                break
            except socket.error as e:
                print(f"Socket error: {e}")
                self.connected = False
                break
        self.sock.settimeout(self.timeout)
        return bytes(data)

    def read_raw_bytes(self, num_bytes, timeout=0.010):
        """Read exactly num_bytes and return raw bytes (no integer conversion)."""
        return self._recv_exact(num_bytes, timeout)

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
        """
        Send val as num_bytes over the TCP socket.
        """
        if not self.connected:
            return
        try:
            self.sock.sendall(int.to_bytes(val, num_bytes, byteorder))
        except socket.error as e:
            print(f"Socket error on send: {e}")
            self.connected = False

    def write_byte_array(self, data):
        """Send a pre-built bytes/bytearray in a single sendall call."""
        if not self.connected:
            return
        try:
            self.sock.sendall(data)
        except socket.error as e:
            print(f"Socket error on send: {e}")
            self.connected = False

    def clear_input_buffer(self):
        """Drain any pending bytes from the socket receive buffer."""
        self.sock.settimeout(0)
        try:
            while self.sock.recv(4096):
                pass
        except (BlockingIOError, socket.timeout):
            pass
        except socket.error:
            pass
        finally:
            self.sock.settimeout(self.timeout)
