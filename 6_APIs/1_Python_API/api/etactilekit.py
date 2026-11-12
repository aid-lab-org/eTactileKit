from .communication import CommunicationSerial, CommunicationWiFi, find_serial_ports, serial_port_kit_id
from .discovery import discover_devices
import numbers
import socket
import struct
from enum import IntEnum


class StimulationMode(IntEnum):
    """Stimulation waveform shape sent to the ESP32."""
    MONOPHASIC = 0       # Single-phase pulse
    BIPHASIC   = 1       # Charge-balanced biphasic pulse
    IMPEDANCE_ONLY = 2   # Every electrode gets the sense pulse (sense pulse height and width) on every scan,
                         # in place of the stimulation pattern; get_voltage_readings() returns what it measures


class StimulationPolarity(IntEnum):
    """Leading phase polarity of the stimulation pulse."""
    CATHODIC = 0   # Cathodic-first (conventional for most neural stimulation)
    ANODIC   = 1   # Anodic-first

PC_ESP32_MEASURE_REQUEST             =0xFF #Request to measure the impedance of all electrodes
PC_ESP32_STIM_PATTERN                =0xFE #Stimulation pattern for all electrodes
PC_ESP32_STIMULATION_POLARITY        =0xFD #Polarity of the stimulation - ANODIC or CATHODIC
PC_ESP32_ELECTRODE_NUM               =0xFC #Number of electrodes used for the stimulation
PC_ESP32_STIMULATION_MODE            =0xFB #Mode of the stimulation
PC_ESP32_STIMULATION_PULSE_WIDTH     =0xFA #Pulse width of the stimulation
PC_ESP32_SENSE_PULSE_HEIGHT          =0xF9 #Pulse height for impedance measurement
PC_ESP32_SENSE_PULSE_WIDTH           =0xF8 #Pulse width for impedance measurement
PC_ESP32_CHANNEL_DISCHARGE_TIME      =0xF7 #Discharge time for the channel
PC_ESP32_STIMULATION_FREQUENCY       =0xF6 #Frequency of the stimulation
PC_ESP32_HV513_NUM_REQUEST           =0xF5 #Request to get the number of HV513 modules used
PC_ESP32_SYNC_CHECK                  =0xF4 #Request to read back the configured electrode number (setup verification)

DEFAULT_BAUDRATE  = 921600
DEFAULT_TCP_PORT  = 8080
AP_MODE_IP        = "192.168.4.1"   # Fixed address of a kit running its own Access Point
MAX_ELECTRODES    = 255             # The electrode number is sent as one byte
MAX_INTENSITY     = 4095            # 12-bit DAC
LINK_CHECK_TIMEOUT = 0.3            # Seconds the kit gets to answer each connection check
READ_TIMEOUT      = 0.1             # Default reply deadline: serial replies take under 1 ms, WiFi ones up to ~40 ms
HV513_TIMEOUT     = 1.0             # The kit answers after the scan in progress (it waits up to 0.5 s for it), plus WiFi delays
SETUP_TIMEOUT     = 1.0             # configure()'s sync check: rides out a WiFi retransmission (0.2-0.5 s)
LATE_REPLY_TIMEOUT = 2.0            # A reply the kit owes that has not arrived by then means the link has failed

# The kit scans every electrode once per period. With a scan that does not fit in the period it scans
# back to back, below the frequency that was set, and it ends a scan after 260 ms, leaving out the
# electrodes it has not reached. estimate_scan_us() sits just above the scan times measured on the
# hardware; settings are refused unless the estimate stays within MAX_SCAN_FRACTION of the period and
# below MAX_SCAN_US, so the kit always stimulates every electrode at the frequency that was set.
SCAN_OVERHEAD_US  = 80              # Per scan: interrupt entry and clearing the HV513 chain
MAX_SCAN_FRACTION = 0.8
MAX_SCAN_US       = 250000


def estimate_scan_us(electrode_number, mode, pulse_width, discharge_time, sense_pulse_width=0):
    """Conservative duration in microseconds of one stimulation scan with these settings."""
    if electrode_number <= 0:
        return 0
    width = sense_pulse_width if mode == StimulationMode.IMPEDANCE_ONLY else pulse_width
    phases = 2 if mode == StimulationMode.BIPHASIC else 1
    return SCAN_OVERHEAD_US + electrode_number * (phases * (max(width, 10) + 8) + discharge_time + 5)


def _check_enum(enum, name, value):
    _check_int(name, value, 0, 0xFF)
    return enum(value)


def _check_int(name, value, low, high):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise TypeError(f"{name} must be an integer, got {value!r}")
    if not low <= value <= high:
        raise ValueError(f"{name} must be {low}-{high}, got {value}")
    return int(value)


class ETactileKit:
    """
    A class to manage and configure an E-Tactile Kit via an ESP32 microcontroller. Use it from one thread.

    This class provides methods for sending parameter configurations (e.g., electrode count,
    stimulation pulse properties, sense pulse properties) and receiving voltage measurements
    from an ESP32. It relies on an external Communication object to handle the low-level
    serial communication.

    Attributes:
        comm (Communication): The communication interface for sending/receiving data
            to/from the ESP32.
        number_of_electrodes (int or None): The kit's electrode number: reported by the kit on connect,
            then set by send_electrode_number().
        stimulation_mode, stimulation_polarity, stimulation_pulse_width (us), sense_pulse_height,
        sense_pulse_width (us), channel_discharge_time (us), stimulation_frequency (Hz): the value this
            connection last sent; None until sent. The kit keeps its settings across connections, so on
            a new connection they are unknown until sent again.
        hv513_num (int or None): The number of HV513 driver chips detected.
        electrode_mapping (list): Maps the electrode indices to the respective hardware channel. mapping[0] means which channel is used for the first electrode in the application and so on.
        voltages (list): Stores the most recent voltage readings from each electrode.
    """

    def __init__(self):
        """
        Initialize the ETactileKit object with a communication interface.
        """

        #------------------------------------------------------------------------------------------#
        # Defined parameters for the ETactile Kit                                                  #
        #------------------------------------------------------------------------------------------#
        self.number_of_electrodes = None
        self._forget_settings()
        self.hv513_num = None
        #------------------------------------------------------------------------------------------#
        # Local parameters                                                                         #
        #------------------------------------------------------------------------------------------#
        self.set_electrode_mapping([])  # Application electrode -> hardware channel
        self.voltages = []  # List to store the voltage readings at the electrodes

        self.comm = None
        self.link = None  # "serial" or "wifi" once connected
        self._owed = 0    # Reply bytes the kit still owes for a request that timed out

    def _forget_settings(self):
        self.stimulation_mode = None
        self.stimulation_polarity = None
        self.stimulation_pulse_width = None
        self.sense_pulse_height = None
        self.sense_pulse_width = None
        self.channel_discharge_time = None
        self.stimulation_frequency = None

    #-------------------------------------------------------------------------------------------------------------#
    # Connecting                                                                                                  #
    # The firmware serves one host at a time: the first host to connect owns the kit and the other link is        #
    # refused until that host disconnects. The kit switches its WiFi radio off while a serial host is connected,  #
    # and zeroes every amplitude whenever a host connects or disconnects.                                         #
    #-------------------------------------------------------------------------------------------------------------#
    def connect(self, mode, serial_port=None, host=None, device_id=None, baudrate=DEFAULT_BAUDRATE,
                tcp_port=DEFAULT_TCP_PORT, timeout=None, discovery_timeout=1.0):
        """
        Connect to the kit over the given link.

        Args:
            mode: "serial" (USB) or "wifi".
            serial_port: serial: port name such as "COM13" or "/dev/ttyACM0". None uses the eTactileKit
                found on USB; with several plugged in, device_id picks one (otherwise the connect is refused).
            host: WiFi: IP address or hostname. None finds the kit by UDP discovery; when no kit answers and
                no device_id is given, the Access Point address 192.168.4.1 is tried.
            device_id: 6-hex kit ID. Selects the kit on USB (through its USB serial number) or over WiFi
                (through discovery), and with serial_port or host given, confirms that kit is there; a kit
                with another ID is never connected.
            baudrate: serial baud rate (the USB port ignores it).
            tcp_port: TCP control port used with `host` and the Access Point fallback.
            timeout: default timeout in seconds of the transport's own reads (the reply methods take
                their own timeouts). None uses 0.02 for serial and 0.10 for WiFi.
            discovery_timeout: seconds discovery listens for replies.

        Returns:
            bool: True once the kit has answered on that link.
        """
        if mode not in ("serial", "wifi"):
            raise ValueError('mode must be "serial" or "wifi"')
        if not self._ready_to_connect():
            return False
        if mode == "serial":
            return self._connect_serial(serial_port, device_id, baudrate, 0.02 if timeout is None else timeout)
        return self._connect_wifi(host, device_id, tcp_port, 0.10 if timeout is None else timeout, discovery_timeout)

    def _connect_serial(self, serial_port, device_id, baudrate, timeout):
        if serial_port:
            if device_id is not None:
                kit = serial_port_kit_id(serial_port)
                if kit != device_id.upper():
                    print(f"{serial_port} is eTactileKit {kit}, not {device_id.upper()}." if kit else
                          f"Cannot confirm that {serial_port} is eTactileKit {device_id.upper()}: it is not listed as "
                          "an eTactileKit port. Pass the port name the system lists, or leave serial_port out.")
                    return False
            port = serial_port
        else:
            ports = find_serial_ports(device_id)
            if not ports:
                print("No eTactileKit found on USB." if device_id is None else
                      f"eTactileKit {device_id.upper()} is not on USB.")
                return False
            if len(ports) > 1:
                print(f"Several eTactileKits on USB ({', '.join(ports)}). Pass serial_port or device_id to choose one.")
                return False
            port = ports[0]
        return self.connect_etactilekit_to_serial(port, baudrate, timeout)

    def _connect_wifi(self, host, device_id, tcp_port, timeout, discovery_timeout):
        if host:
            if device_id is not None:
                # Confirm through discovery that the kit with this ID is at host (a DHCP address can move).
                target = next((d for d in discover_devices(timeout=discovery_timeout)
                               if d["id"].upper() == device_id.upper()), None)
                try:
                    host_ip = socket.gethostbyname(host)
                except OSError:
                    host_ip = host
                if target is None or target["ip"] != host_ip:
                    where = f"it is at {target['ip']}" if target else "it did not answer discovery"
                    print(f"Cannot confirm that {host} is eTactileKit {device_id.upper()}: {where}.")
                    return False
            return self.connect_etactilekit_to_wifi(host, tcp_port, timeout)
        devices = discover_devices(timeout=discovery_timeout)
        if devices:
            return self._connect_discovered(devices, device_id, None, timeout)
        if device_id is not None:
            # The Access Point address could belong to any kit, so it is no substitute for a requested one.
            print(f"eTactileKit {device_id.upper()} did not answer discovery "
                  "(a kit connected over USB serial has its WiFi switched off).")
            return False
        print(f"No eTactileKit answered discovery; trying the Access Point address {AP_MODE_IP}.")
        return self.connect_etactilekit_to_wifi(AP_MODE_IP, tcp_port, timeout, connect_timeout=3.0)

    def connect_etactilekit_to_serial(self, ser_port, baudrate=DEFAULT_BAUDRATE, timeout=0.02):
        """
        Connect to the kit over USB serial.

        Returns:
            bool: True if the kit answered on this port. False if the port could not be opened or
            the kit did not answer (it is connected to a WiFi host).
        """
        if not self._ready_to_connect():
            return False
        comm = CommunicationSerial(ser_port, baudrate, timeout)
        if not comm.connect():
            return False
        return self._claim_link(comm, "serial", f"USB serial ({ser_port})",
                                "no answer: the kit is connected to a WiFi host, or is not running eTactileKit firmware")

    def connect_etactilekit_to_wifi(self, ip, port=DEFAULT_TCP_PORT, timeout=0.10, connect_timeout=5.0):
        """
        Connect to the kit over WiFi (TCP).

        Returns:
            bool: True if the kit accepted the connection and answered.
        """
        if not self._ready_to_connect():
            return False
        comm = CommunicationWiFi(ip, port, timeout)
        if not comm.connect(connect_timeout):
            return False
        return self._claim_link(comm, "wifi", f"WiFi ({ip}:{port})", "no answer from the kit")

    def connect_by_discovery(self, device_id=None, port=None, timeout=0.10, discovery_timeout=1.0):
        """
        Find eTactileKit boards on the LAN via UDP broadcast discovery and connect over WiFi.

        This is the recommended way to connect in station (STA) mode when several kits share
        one router: each board is found by its unique 6-hex ID (printed on its label, or listed by
        "python -m api.discovery") regardless of the DHCP-assigned IP, without relying on mDNS/.local.

        Args:
            device_id: connect to the board with this ID (case-insensitive). None connects to
                the only board found (and reports an error if more than one is present).
            port: TCP control port override; defaults to the port reported by the board (8080).
            timeout: socket read timeout for the control connection.
            discovery_timeout: seconds discovery listens for replies.

        Returns:
            bool: True if a free board was found and answered over TCP.
        """
        devices = discover_devices(timeout=discovery_timeout)
        if not devices:
            print("No eTactileKit boards discovered. Check the shared router, or use AP mode. "
                  "A kit connected over USB serial has its WiFi switched off.")
            return False
        return self._connect_discovered(devices, device_id, port, timeout)

    def _connect_discovered(self, devices, device_id, port, timeout):
        """Pick the target from discovery replies and connect to it over TCP."""
        if device_id is None:
            if len(devices) > 1:
                ids = ", ".join(d["id"] for d in devices)
                print(f"Multiple boards found ({ids}). Pass device_id to choose one.")
                return False
            target = devices[0]
        else:
            target = next((d for d in devices if d["id"].upper() == device_id.upper()), None)
            if target is None:
                ids = ", ".join(d["id"] for d in devices) or "none"
                print(f"Board '{device_id}' not found. Discovered: {ids}")
                return False

        if target.get("busy"):
            print(f"eTactileKit {target['id']} is in use by another WiFi host.")
            return False
        tcp_port = port if port is not None else target["port"]
        print(f"Discovered eTactileKit {target['id']} at {target['ip']}:{tcp_port} ({target['mode']}).")
        return self.connect_etactilekit_to_wifi(target["ip"], tcp_port, timeout)

    def disconnect_etactilekit(self):
        """
        Turn every output off and disconnect from the kit. The kit also zeroes every amplitude once it
        notices its host has gone, which takes 0.25 s after a serial port closes.
        """
        if self._connected():
            if self.number_of_electrodes:
                self.comm.write_byte_array(bytes([PC_ESP32_STIM_PATTERN]) + bytes(2 * self.number_of_electrodes))
            if self._connected():
                self.comm.write_byte_array(bytes([PC_ESP32_SENSE_PULSE_HEIGHT, 0]))
        if self.comm:
            self.comm.disconnect()
        self.comm = None
        self.link = None
        self._owed = 0

    def _ready_to_connect(self):
        """False if a link is already open; otherwise clears a link that has dropped."""
        if self._connected():
            print("Already connected. Disconnect first before connecting again.")
            return False
        if self.comm:
            self.comm.disconnect()
            self.comm = None
        self.link = None
        return True

    def _connected(self):
        return self.comm is not None and self.comm.connected

    def _claim_link(self, comm, link, label, refused_reason):
        """Keep comm only if the kit answers on it: the firmware answers only the host that owns it.
        Two sync requests must bring back exactly two equal bytes (the kit's electrode number), so a
        byte left over from an earlier session cannot pass; the check is repeated on a cleared buffer.
        The electrode number the kit reports is adopted, because stimulation frames are framed by it."""
        for _ in range(3):
            if not comm.connected:
                break
            comm.clear_input_buffer()
            if not comm.write_byte_array(bytes([PC_ESP32_SYNC_CHECK, PC_ESP32_SYNC_CHECK])):
                break
            reply = comm.read_raw_bytes(2, timeout=LINK_CHECK_TIMEOUT)
            if (len(reply) == 2 and reply[0] == reply[1] and not comm.read_raw_bytes(64, timeout=0.02)
                    and comm.connected):
                if self.number_of_electrodes is not None and self.number_of_electrodes != reply[0]:
                    print(f"[WARN] The kit is set to {reply[0]} electrodes, not {self.number_of_electrodes}; "
                          "run configure() again before sending patterns.")
                self.number_of_electrodes = reply[0]
                self._forget_settings()
                self.hv513_num = None
                self.comm = comm
                self.link = link
                self._owed = 0
                print(f"Connected to eTactileKit over {label}.")
                return True
        print(f"{label}: {refused_reason}.")
        comm.disconnect()
        return False

    #-------------------------------------------------------------------------------------------------------------#
    # Setup                                                                                                        #
    # The kit does not acknowledge settings; sync_check() confirms the link and the electrode number. Each send_*  #
    # method returns True once sent, False if the link is not open or failed, or if the setting was refused        #
    # because the scan would not fit in the period or cannot be checked. Values outside the protocol's range raise #
    # ValueError (TypeError for non-integers).                                                                     #
    #-------------------------------------------------------------------------------------------------------------#
    def configure(self, electrode_number, mode, pulse_width, frequency, polarity=StimulationPolarity.ANODIC,
                  discharge_time=50, sense_pulse_height=0, sense_pulse_width=0, electrode_mapping=None):
        """
        Set the kit up for stimulation and verify it. Each setting takes effect while the kit keeps scanning at
        its current (possibly a previous host's) period, so the electrode number goes to 0 first and to its
        real value last: no intermediate state can overrun. Then the sync check must report electrode_number,
        and the HV513 count is read (a warning if it gives fewer outputs than electrodes).

        Args:
            electrode_number: electrodes to scan (0-255).
            mode: StimulationMode (or its value).
            pulse_width: stimulation pulse width in us (0-65535).
            frequency: stimulation frequency in Hz (1-65535).
            polarity: StimulationPolarity (or its value).
            discharge_time: channel discharge time in us (0-255).
            sense_pulse_height, sense_pulse_width: sense pulse used in IMPEDANCE_ONLY mode (0-255 each; the
                height is 0-255 of the 12-bit DAC range, the width is in us).
            electrode_mapping: application electrode -> hardware channel; None maps electrode i to channel i.

        Returns:
            bool: True once the kit reports the new electrode number. False, with the reason printed, if the
            scan would not fit in the period (nothing is sent), or, after disconnecting, if the link failed
            or the sync check did not match.
        """
        electrode_number = _check_int("electrode_number", electrode_number, 0, MAX_ELECTRODES)
        mode = _check_enum(StimulationMode, "mode", mode)
        polarity = _check_enum(StimulationPolarity, "polarity", polarity)
        pulse_width = _check_int("pulse_width", pulse_width, 0, 0xFFFF)
        frequency = _check_int("frequency", frequency, 1, 0xFFFF)
        discharge_time = _check_int("discharge_time", discharge_time, 0, 0xFF)
        sense_pulse_height = _check_int("sense_pulse_height", sense_pulse_height, 0, 0xFF)
        sense_pulse_width = _check_int("sense_pulse_width", sense_pulse_width, 0, 0xFF)
        mapping = list(range(electrode_number)) if electrode_mapping is None else list(electrode_mapping)
        if len(mapping) != electrode_number:
            raise ValueError(f"electrode_mapping has {len(mapping)} entries, not {electrode_number}")
        if not self._connected():
            print("Not connected to an eTactileKit.")
            return False
        if not self._scan_fits(electrode_number, mode, pulse_width, discharge_time, sense_pulse_width, frequency):
            return False
        self.set_electrode_mapping(mapping)

        steps = (lambda: self.send_electrode_number(0),
                 lambda: self.send_stimulation_frequency(frequency),
                 lambda: self.send_stimulation_mode(mode),
                 lambda: self.send_stimulation_polarity(polarity),
                 lambda: self.send_stimulation_pulse_width(pulse_width),
                 lambda: self.send_sense_pulse_height(sense_pulse_height),
                 lambda: self.send_sense_pulse_width(sense_pulse_width),
                 lambda: self.send_channel_discharge_time(discharge_time),
                 lambda: self.send_electrode_number(electrode_number))
        for step in steps:
            if not step():
                return self._abort_setup("the link failed" if not self._connected() else "a setting was refused")

        sync = self.sync_check(timeout=SETUP_TIMEOUT)
        if sync != [electrode_number]:
            return self._abort_setup("the link failed" if not self._connected() else
                                     f"the kit reports {sync[0] if sync else 'nothing'} instead of "
                                     f"{electrode_number} electrodes")
        hv513 = self.update_and_get_hv513_count()
        if not self._connected():
            return self._abort_setup("the link failed")
        if hv513 is not None and hv513 * 8 < electrode_number:
            print(f"[WARN] The kit detects {hv513} HV513 chips ({hv513 * 8} outputs), fewer than "
                  f"{electrode_number} electrodes.")
        return True

    def _abort_setup(self, reason):
        print(f"Setup failed: {reason}. Disconnected.")
        self.disconnect_etactilekit()
        return False

    def send_electrode_number(self, electrode_number):
        """
        Send electrode number to ESP32

        Args:
            electrode_number: The number of electrodes used in the application (0-255).
        """
        electrode_number = _check_int("electrode_number", electrode_number, 0, MAX_ELECTRODES)
        if not self._scan_fits(electrode_number=electrode_number):
            return False
        if not self._send(bytes([PC_ESP32_ELECTRODE_NUM, electrode_number])):
            return False
        self.number_of_electrodes = electrode_number
        return True

    def send_stimulation_mode(self, mode):
        """
        Send stimulation Mode to ESP32

        Args:
            mode: StimulationMode (or its value).
        """
        mode = _check_enum(StimulationMode, "mode", mode)
        if not self._scan_fits(mode=mode):
            return False
        if not self._send(bytes([PC_ESP32_STIMULATION_MODE, mode])):
            return False
        self.stimulation_mode = mode
        return True

    def send_stimulation_polarity(self, polarity):
        """
        Send stimulation polarity to ESP32

        Args:
            polarity: StimulationPolarity (or its value): 1 for Anodic, 0 for Cathodic.
        """
        polarity = _check_enum(StimulationPolarity, "polarity", polarity)
        if not self._send(bytes([PC_ESP32_STIMULATION_POLARITY, polarity])):
            return False
        self.stimulation_polarity = polarity
        return True

    def send_stimulation_pulse_width(self, pulse_width):
        """
        Send stimulation pulse width to ESP32

        Args:
            pulse_width (int): The pulse width for stimulation in us (0-65535).
        """
        pulse_width = _check_int("pulse_width", pulse_width, 0, 0xFFFF)
        if not self._scan_fits(pulse_width=pulse_width):
            return False
        if not self._send(bytes([PC_ESP32_STIMULATION_PULSE_WIDTH]) + struct.pack('<H', pulse_width)):
            return False
        self.stimulation_pulse_width = pulse_width
        return True

    def send_sense_pulse_height(self, pulse_height):
        """
        Send sense pulse height to ESP32

        Args:
            pulse_height (int): The height of the sense pulse, 0-255 of the 12-bit DAC range. The kit sends it
                to every electrode on every scan in IMPEDANCE_ONLY mode, in place of the stimulation pattern;
                keep it below the sensation threshold.
        """
        pulse_height = _check_int("pulse_height", pulse_height, 0, 0xFF)
        if not self._send(bytes([PC_ESP32_SENSE_PULSE_HEIGHT, pulse_height])):
            return False
        self.sense_pulse_height = pulse_height
        return True

    def send_sense_pulse_width(self, pulse_width):
        """
        Send sense pulse width to ESP32

        Args:
            pulse_width (int): The width of the sense pulse in us (0-255), used in IMPEDANCE_ONLY mode. This
                value should be considered along with the sense pulse height to ensure that the created sense
                pulse does not stimulate.
        """
        pulse_width = _check_int("pulse_width", pulse_width, 0, 0xFF)
        if not self._scan_fits(sense_pulse_width=pulse_width):
            return False
        if not self._send(bytes([PC_ESP32_SENSE_PULSE_WIDTH, pulse_width])):
            return False
        self.sense_pulse_width = pulse_width
        return True

    def send_channel_discharge_time(self, discharge_time):
        """
        Send channel discharge time to ESP32

        Args:
            discharge_time (int): The time in us (0-255) taken to discharge the channel after stimulation.
        """
        discharge_time = _check_int("discharge_time", discharge_time, 0, 0xFF)
        if not self._scan_fits(discharge_time=discharge_time):
            return False
        if not self._send(bytes([PC_ESP32_CHANNEL_DISCHARGE_TIME, discharge_time])):
            return False
        self.channel_discharge_time = discharge_time
        return True

    def send_stimulation_frequency(self, stim_freq):
        """
        Send stimulation frequency to ESP32

        Args:
            stim_freq (int): The frequency for stimulation pulses in Hz (1-65535).
        """
        stim_freq = _check_int("stim_freq", stim_freq, 1, 0xFFFF)
        if not self._scan_fits(frequency=stim_freq):
            return False
        if not self._send(bytes([PC_ESP32_STIMULATION_FREQUENCY]) + struct.pack('<H', stim_freq)):
            return False
        self.stimulation_frequency = stim_freq
        return True

    def _send(self, frame):
        if not self._connected():
            print("Not connected to an eTactileKit.")
            return False
        return self.comm.write_byte_array(frame)

    def _scan_fits(self, electrode_number=None, mode=None, pulse_width=None, discharge_time=None,
                   sense_pulse_width=None, frequency=None):
        """True if one scan with these settings (the ones not given: as this connection last sent them) stays
        within MAX_SCAN_FRACTION of the period and below MAX_SCAN_US. With 0 electrodes every setting fits.
        While the kit scans electrodes, a setting that changes the scan time can only be checked once this
        connection has sent every setting the scan time depends on."""
        if not self._connected():
            return True   # Nothing can be sent; _send() reports it
        n = self.number_of_electrodes if electrode_number is None else electrode_number
        mode = self.stimulation_mode if mode is None else mode
        pulse_width = self.stimulation_pulse_width if pulse_width is None else pulse_width
        discharge_time = self.channel_discharge_time if discharge_time is None else discharge_time
        sense_pulse_width = self.sense_pulse_width if sense_pulse_width is None else sense_pulse_width
        frequency = self.stimulation_frequency if frequency is None else frequency
        if not n:
            return True
        needed = [("mode", mode),
                  ("sense pulse width" if mode == StimulationMode.IMPEDANCE_ONLY else "pulse width",
                   sense_pulse_width if mode == StimulationMode.IMPEDANCE_ONLY else pulse_width),
                  ("discharge time", discharge_time), ("frequency", frequency)]
        unknown = [name for name, value in needed if value is None]
        if unknown:
            print(f"Not sent: the kit scans {n} electrodes and this connection has not set its "
                  f"{', '.join(unknown)}, so the scan time cannot be checked. Send electrode number 0 first, "
                  "then the settings, then the electrode number - configure() does this.")
            return False
        scan_us = estimate_scan_us(n, mode, pulse_width, discharge_time, sense_pulse_width)
        period_us = 1000000 // frequency
        limit_us = min(MAX_SCAN_FRACTION * period_us, MAX_SCAN_US)
        if scan_us <= limit_us:
            return True
        if scan_us > MAX_SCAN_US:
            fix = "Lower the electrode count, the pulse width or the discharge time."
        else:
            max_freq = int(1000000 // -(-scan_us // MAX_SCAN_FRACTION))
            fix = (f"Lower the frequency to {max_freq} Hz or less, or the electrode count, the pulse width or the "
                   "discharge time.")
        print(f"Not sent: one scan of {n} electrodes would take about {scan_us / 1000:.1f} ms, more than "
              f"{limit_us / 1000:.1f} ms ({int(MAX_SCAN_FRACTION * 100)}% of the {period_us / 1000:.1f} ms period at "
              f"{frequency} Hz, at most {MAX_SCAN_US / 1000:.0f} ms). A scan that reaches its period makes "
              f"the kit stimulate below the set frequency or leave electrodes out. {fix}")
        return False

    #-------------------------------------------------------------------------------------------------------------#
    # Stimulation                                                                                                  #
    #-------------------------------------------------------------------------------------------------------------#
    def send_stim_pattern(self, stim_pattern):
        """
        Send stimulation pattern to ESP32

        Args:
            stim_pattern (list): n pulse heights (0-4095, the 12-bit DAC range; values outside it are
                clamped), one per application electrode, in application order.

        Returns:
            bool: True once the pattern has been sent. False if nothing was sent because the link is not open
                or the pattern or the electrode mapping does not match the electrode number, or if the link
                failed (the link is then closed and the kit zeroes every amplitude).
        """
        if not self._connected():
            return False
        n = self.number_of_electrodes
        if n is None or len(stim_pattern) != n:
            print("Stimulation pattern length should be equal to the number of electrodes")
            return False
        if len(self.electrode_mapping) != n:
            print("Electrode mapping length should be equal to the number of electrodes (see set_electrode_mapping)")
            return False
        # Apply electrode mapping into the pre-allocated buffer (no new list allocation)
        mapped  = self._mapped_buf
        mapping = self.electrode_mapping
        for ch in range(n):
            mapped[mapping[ch]] = max(0, min(int(stim_pattern[ch]), MAX_INTENSITY)) # The DAC is 12 bit

        # Pack all electrode values directly into the reused packet buffer and send in one write
        struct.pack_into(self._stim_pack_fmt, self._packet_buf, 1, *mapped)
        return self.comm.write_byte_array(self._packet_buf)

    #-------------------------------------------------------------------------------------------------------------#
    # Requests                                                                                                     #
    #-------------------------------------------------------------------------------------------------------------#
    def _request(self, command, reply_len, timeout):
        """Send a one-byte request and read its reply (shorter on timeout or link failure). The kit answers
        every request in order, so a reply that arrives late would be read as the answer to the next request:
        the bytes it still owes are read and discarded before the next request is sent. A reply still missing
        after LATE_REPLY_TIMEOUT means the link has failed, and it is closed."""
        if not self._connected():
            return b""
        if self._owed:
            late = self.comm.read_raw_bytes(self._owed, timeout=LATE_REPLY_TIMEOUT)
            if len(late) < self._owed:
                if self._connected():
                    print(f"[WARN] A reply the kit owes did not arrive within {LATE_REPLY_TIMEOUT} s; closing the link.")
                    self.comm.disconnect()
                self._owed = 0
                return b""
            self._owed = 0
        self.comm.clear_input_buffer()
        if not self.comm.write_byte_array(bytes([command])):
            return b""
        raw = self.comm.read_raw_bytes(reply_len, timeout=timeout)
        self._owed = reply_len - len(raw) if self._connected() else 0
        return raw

    def get_voltage_readings(self, timeout=READ_TIMEOUT):
        """
        Read the voltage data from the ESP32 corresponding to the number of electrodes defined in the application.

        Reads all electrode voltages in a single bulk receive instead of N separate
        calls, reducing socket overhead proportional to electrode count.

        Returns:
            list: The voltage reading of each electrode in application order, or None if not connected, if the
                kit did not answer within timeout seconds, or if the electrode mapping does not match.
        """
        if not self._connected():
            return None
        n = self.number_of_electrodes
        if n is None or len(self.electrode_mapping) != n:
            print("Electrode mapping length should be equal to the number of electrodes (see set_electrode_mapping)")
            return None
        raw = self._request(PC_ESP32_MEASURE_REQUEST, n * 2, timeout)
        if len(raw) == n * 2:
            temp_voltages = list(struct.unpack(f'<{n}H', raw))
            self.voltages = [temp_voltages[self.electrode_mapping[i]] for i in range(n)]
            return self.voltages
        else:
            print(f"[WARN] get_voltage_readings: expected {n * 2} bytes, got {len(raw)}")
            return None

    def update_and_get_hv513_count(self, timeout=HV513_TIMEOUT):
        """
        Get the count of HV513 driver chips (8 outputs each) the kit detects. Each stacked switching
        module adds 8 (standard board) or 4 (compact board). The kit finishes the stimulation scan in progress,
        skips stimulation while it senses, then answers.

        Returns:
            int: The number of HV513 driver chips, or None if the kit did not answer within timeout seconds.
        """
        raw = self._request(PC_ESP32_HV513_NUM_REQUEST, 1, timeout)
        if len(raw) != 1:
            print("[WARN] update_and_get_hv513_count: no answer from the kit")
            self.hv513_num = None
            return None
        self.hv513_num = raw[0]
        return self.hv513_num

    def sync_check(self, timeout=READ_TIMEOUT):
        """
        Ask the kit for its electrode number to confirm the link.

        Returns:
            list: The bytes received (one byte, the electrode number, from a kit that owns this link);
                empty if it did not answer within timeout seconds.
        """
        return list(self._request(PC_ESP32_SYNC_CHECK, 1, timeout))

    #-------------------------------------------------------------------------------------------------------------#
    # General Functions
    #-------------------------------------------------------------------------------------------------------------#
    def set_electrode_mapping(self, electrode_mapping):
        """
        Set the electrode mapping for all the electrodes used in the application.
        For example: the electrode index 0 in your application should be mapped accordingly so that the corresponding hardware electrode is mapped to electrode 0

        Args:
            electrode_mapping (list): A list of n integers representing the mapping of the n electrodes.
                This means what application electrode is relevant to which hardware electrode in order.
                Each hardware index 0..n-1 must appear exactly once.
        """
        n = len(electrode_mapping)
        if n > MAX_ELECTRODES:
            raise ValueError(f"electrode_mapping can have at most {MAX_ELECTRODES} entries")
        if sorted(electrode_mapping) != list(range(n)):
            raise ValueError("electrode_mapping must list each hardware index 0..n-1 exactly once")
        self.electrode_mapping = list(electrode_mapping)
        # Pre-allocate reusable buffers for send_stim_pattern to avoid per-call allocation
        self._mapped_buf    = [0] * n
        self._stim_pack_fmt = f'<{n}H'
        self._packet_buf    = bytearray(1 + n * 2)
        self._packet_buf[0] = PC_ESP32_STIM_PATTERN
    #-------------------------------------------------------------------------------------------------------------#
    # Safety checking to check whether the changes done are safe or not
    #-------------------------------------------------------------------------------------------------------------#
    def check_valid_initialization(self):
        """
        Check the safety and the validity of the parameters set for the application.
        The function will check whether the parameters set are safe or not.

        Returns:
            bool: True if all parameters are set correctly, False otherwise.
        """
        if self.number_of_electrodes is None:
            print("Number of electrodes is not set")
            return False
        if self.stimulation_mode is None:
            print("Stimulation mode is not set")
            return False
        if self.stimulation_polarity is None:
            print("Stimulation polarity is not set")
            return False
        if self.stimulation_pulse_width is None:
            print("Stimulation pulse width is not set")
            return False
        if self.sense_pulse_height is None:
            print("Sense pulse height is not set")
            return False
        if self.sense_pulse_width is None:
            print("Sense pulse width is not set")
            return False
        if self.channel_discharge_time is None:
            print("Channel discharge time is not set")
            return False
        if self.stimulation_frequency is None:
            print("Stimulation frequency is not set")
            return False
        if self.hv513_num is None:
            print("HV513 count is not set")
            return False
        if self.hv513_num*8 < self.number_of_electrodes:
            print("Number of electrodes exceeds the number of outputs connected.\nPlease check the number of stacked switching modules")
            return False
        if not self._scan_fits():
            return False

        print("All parameters are set")
        return True
