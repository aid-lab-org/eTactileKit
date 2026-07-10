from .communication import CommunicationSerial, CommunicationWiFi #,CommunicationBLE
import struct
from enum import IntEnum


class StimulationMode(IntEnum):
    """Stimulation waveform shape sent to the ESP32."""
    MONOPHASIC = 0   # Single-phase pulse
    BIPHASIC   = 1   # Charge-balanced biphasic pulse
    IMPEDANCE_ONLY = 2   # Special mode for impedance measurement (no actual stimulation)


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

class ETactileKit:
    """
    A class to manage and configure an E-Tactile Kit via an ESP32 microcontroller.

    This class provides methods for sending parameter configurations (e.g., electrode count,
    stimulation pulse properties, sense pulse properties) and receiving voltage measurements
    from an ESP32. It relies on an external Communication object to handle the low-level
    serial communication.

    Attributes:
        comm (Communication): The communication interface for sending/receiving data 
            to/from the ESP32.
        stimulation_polarity (int): Stimulation polarity mode (1 for Anodic, 0 for Cathodic).
        number_of_electrodes (int or None): The total number of electrodes in use.
        stimulation_pulse_height (int or None): The pulse height for stimulation.
        stimulation_pulse_width (int or None): The pulse width in µs for stimulation.
        sense_pulse_height (int or None): The pulse height for sensing.
        sense_pulse_width (int or None): The pulse width µs for sensing.
        channel_discharge_time (int or None): The time µs taken to discharge
            the channel after stimulation.
        stimulation_frequency (int or None): The frequency in Hz
            for stimulation pulses.
        hv513_num (int or None): The number of HV513 driver chips detected.
        electrode_mapping (list): Maps the electrode indices to the respective hardware channel. mapping[0] means which channel is used for the first electrode in the application ans so on.
            electrode indices.
        voltages (list): Stores the most recent voltage readings from each electrode.
    """

    def __init__(self):
        """
        Initialize the ETactileKit object with a communication interface.
        """

        #------------------------------------------------------------------------------------------#
        # Defined parameters for the ETactile Kit                                                  #
        #------------------------------------------------------------------------------------------#
        self.stimulation_polarity = 1  # 1 for Anodic, 0 for Cathodic
        self.number_of_electrodes = None
        self.stimulation_mode = None
        self.stimulation_pulse_height = None
        self.stimulation_pulse_width = None
        self.sense_pulse_height = None
        self.sense_pulse_width = None
        self.channel_discharge_time = None
        self.stimulation_frequency = None
        self.hv513_num = None
        #------------------------------------------------------------------------------------------#
        # Local parameters                                                                         #
        #------------------------------------------------------------------------------------------#
        self.electrode_mapping = []  # List to store the electrode mapping
        self.voltages = []  # List to store the voltage readings at the electrodes

        self.comm = None

    def connect_etactilekit_to_serial(self, ser_port, baudrate, timeout=0.02):
        """
        Connect to the ESP32 device using the Communication object.

        Returns:
            True if connection is successful (Serial)
        """
        if self.comm and self.comm.connected:
            print("Already connected to a communication interface. Please disconnect first before connecting to another interface.")
            return
        self.comm = CommunicationSerial(ser_port, baudrate, timeout)
        self.comm.connect()

    def connect_etactilekit_to_wifi(self, ip, port, timeout=0.02):
        """
        Connect to the ESP32 device via WiFi (TCP).

        If a previous connection attempt failed (comm exists but not connected),
        it is cleaned up before retrying.

        Returns:
            bool: True if the TCP connection is successfully established.
        """
        if self.comm and self.comm.connected:
            print("Already connected. Disconnect first before connecting to another interface.")
            return False
        if self.comm:
            self.comm.disconnect()
            self.comm = None
        self.comm = CommunicationWiFi(ip, port, timeout)
        return self.comm.connect()

    def connect_by_discovery(self, device_id=None, port=None, timeout=0.02, discovery_timeout=1.0):
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
            discovery_timeout: seconds to wait for discovery replies.

        Returns:
            bool: True if a board was found and the TCP connection succeeded.
        """
        from .discovery import discover_devices
        devices = discover_devices(timeout=discovery_timeout)
        if not devices:
            print("No eTactileKit boards discovered. Check the shared router, or use AP mode.")
            return False

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

        tcp_port = port if port is not None else target["port"]
        print(f"Discovered eTactileKit {target['id']} at {target['ip']}:{tcp_port} ({target['mode']}).")
        return self.connect_etactilekit_to_wifi(target["ip"], tcp_port, timeout)

    def disconnect_etactilekit(self):
        """
        Disconnect from the ESP32 device.

        Returns:
            bool: True if the disconnection is successful, False otherwise.
        """
        self.comm.disconnect()
        self.comm = None

    #-------------------------------------------------------------------------------------------------------------#
    # Functions to handle the communication between the PC and the ESP32 and setup parameters                     #
    #-------------------------------------------------------------------------------------------------------------#
    def send_electrode_number(self, electrode_number):
        """
        Send electrode number to ESP32
        Args:
            electrode_number: The number of electrodes used in the application.
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_ELECTRODE_NUM, electrode_number]))
        self.number_of_electrodes = electrode_number

    def send_stimulation_mode(self, mode):
        """
        Send stimulation Mode to ESP32
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_STIMULATION_MODE, mode]))
        self.stimulation_mode = mode

    def send_stimulation_polarity(self, polarity):
        """
        Send stimulation polarity to ESP32

        Args:
            polarity (int): 1 for Anodic, 0 for Cathodic.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_STIMULATION_POLARITY, polarity]))
        self.stimulation_polarity = polarity

    def send_stimulation_pulse_width(self, pulse_width):
        """
        Send stimulation pulse width to ESP32

        Args:
            pulse_width (int): The pulse width for stimulation.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_STIMULATION_PULSE_WIDTH]) + struct.pack('<H', pulse_width))
        self.stimulation_pulse_width = pulse_width

    def send_sense_pulse_height(self, pulse_height):
        """
        Send sense pulse height to ESP32

        Args:
            pulse_height (int): The pulse height used for sensing. This should be a smaller value than the stimulation pulse height so that it does not affect the stimulation but only senses the voltage.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_SENSE_PULSE_HEIGHT, pulse_height]))
        self.sense_pulse_height = pulse_height

    def send_sense_pulse_width(self, pulse_width):
        """
        Send sense pulse width to ESP32

        Args:
            pulse_width (int): The pulse width used for sensing. This value should be considered along with the sense pulse height to ensure that the created sense pulse does not stimulate.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_SENSE_PULSE_WIDTH, pulse_width]))
        self.sense_pulse_width = pulse_width

    def send_channel_discharge_time(self, discharge_time):
        """
        Send channel discharge time to ESP32

        Args:
            discharge_time (int): The time taken to discharge the channel after stimulation.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_CHANNEL_DISCHARGE_TIME, discharge_time]))
        self.channel_discharge_time = discharge_time

    def send_stimulation_frequency(self, stim_freq):
        """
        Send stimulation frequency to ESP32

        Args:
            stim_freq (int): The frequency for stimulation pulses.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_byte_array(bytes([PC_ESP32_STIMULATION_FREQUENCY]) + struct.pack('<H', stim_freq))
        self.stimulation_frequency = stim_freq


    def send_stim_pattern(self, stim_pattern):
        """
        Send stimulation pattern to ESP32

        Args:
            stim_pattern (list): A list of n integers(8bit representable - 0 < x <255) representing the intensity values of the n electrodes.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        n = self.number_of_electrodes
        if len(stim_pattern) != n:
            print("Stimulation pattern length should be equal to the number of electrodes")
            return False
        # Apply electrode mapping into the pre-allocated buffer (no new list allocation)
        mapped  = self._mapped_buf
        mapping = self.electrode_mapping
        for ch in range(n):
            mapped[mapping[ch]] =  min(stim_pattern[ch], 4095) # The maximum pulse height that can be set is 4095 since the DAC is 12 bit

        # Pack all electrode values directly into the reused packet buffer and send in one write
        struct.pack_into(self._stim_pack_fmt, self._packet_buf, 1, *mapped)
        self.comm.write_byte_array(self._packet_buf)

    
    def get_voltage_readings(self, timeout=0.05):
        """
        Read the voltage data from the ESP32 corresponding to the number of electrodes defined in the application.

        Reads all electrode voltages in a single bulk receive instead of N separate
        calls, reducing socket overhead proportional to electrode count.

        Returns:
            list: A list of voltage readings from each electrode.
        """
        n = self.number_of_electrodes
        self.comm.clear_input_buffer()  # flush stale bytes BEFORE request to prevent buffer contamination
        self.comm.write_byte_array(bytes([PC_ESP32_MEASURE_REQUEST]))
        raw = self.comm.read_raw_bytes(n * 2, timeout=timeout)
        if len(raw) == n * 2:
            temp_voltages = list(struct.unpack(f'<{n}H', raw))
            self.voltages = [temp_voltages[self.electrode_mapping[i]] for i in range(n)]
            return self.voltages
        else:
            print(f"[WARN] get_voltage_readings: expected {n * 2} bytes, got {len(raw)}")
            return None

    def update_and_get_hv513_count(self, timeout=0.05):
        """
        Get the count of HV513s connected. If only the main controller module is used this value will be 1. Each switching module adds 8 more HV513s
        
        Returns:
            int: The number of HV513 driver chips connected to the ESP32.
        """
        self.comm.clear_input_buffer()
        self.comm.write_byte_array(bytes([PC_ESP32_HV513_NUM_REQUEST]))
        received_data = self.comm.read_bytes_with_timeout(num_bytes=1, timeout=timeout)
        self.hv513_num = received_data
        return received_data
    
    def sync_check(self, num_bytes=1, timeout=0.05):
        self.comm.clear_input_buffer()
        self.comm.write_byte_array(bytes([PC_ESP32_SYNC_CHECK]))
        received_data = self.comm.read_raw_bytes(num_bytes=num_bytes, timeout=timeout)
        # Convert the returned bytes/bytearray into a list of integers
        converted_data = list(received_data)

        return converted_data

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
        """
        self.electrode_mapping = electrode_mapping
        n = len(electrode_mapping)
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
        
        print("All parameters are set")
        return True