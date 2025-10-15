from .communication import Communication

PC_ESP32_MEASURE_REQUEST             =0xFF #Request to measure the impedance of all electrodes       
PC_ESP32_STIM_PATTERN                =0xFE #Stimulation pattern for all electrodes
PC_ESP32_STIMULATION_POLARITY        =0xFD #Polarity of the stimulation - ANODIC or CATHODIC
PC_ESP32_ELECTRODE_NUM               =0xFC #Number of electrodes used for the stimulation
PC_ESP32_STIMULATION_PULSE_HEIGHT    =0xFB #Pulse height of the stimulation
PC_ESP32_STIMULATION_PULSE_WIDTH     =0xFA #Pulse width of the stimulation
PC_ESP32_SENSE_PULSE_HEIGHT          =0xF9 #Pulse height for impedance measurement
PC_ESP32_SENSE_PULSE_WIDTH           =0xF8 #Pulse width for impedance measurement
PC_ESP32_CHANNEL_DISCHARGE_TIME      =0xF7 #Discharge time for the channel
PC_ESP32_STIMULATION_FREQUENCY       =0xF6 #Frequency of the stimulation
PC_ESP32_HV513_NUM_REQUEST           =0xF5 #Request to get the number of HV513 modules used

# ESP32_PC_RECEIVE_FINISHED            =0xAA #Indicates that the ESP32 has received the data from the PC

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

    def __init__(self, port_name, baudrate, timeout=0.02):
        """
        Initialize the ETactileKit object with a communication interface.

        Args:
            port_name (str): The name of the serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux).
            baudrate (int): The communication speed in baud.
            timeout (float, optional): The default timeout for serial read operations. Defaults to 0.02.
        """
        self.comm = Communication(port_name, baudrate, timeout)  # Communication object for serial communication tasks
        #------------------------------------------------------------------------------------------#
        # Defined parameters for the ETactile Kit                                                  #
        #------------------------------------------------------------------------------------------#
        self.stimulation_polarity = 1  # 1 for Anodic, 0 for Cathodic
        self.number_of_electrodes = None
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

    def connect_etactilekit(self):
        """
        Connect to the ESP32 device using the Communication object.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        return self.comm.connect()

    def disconnect_etactilekit(self):
        """
        Disconnect from the ESP32 device.

        Returns:
            bool: True if the disconnection is successful, False otherwise.
        """
        return self.comm.disconnect()

    #-------------------------------------------------------------------------------------------------------------#
    # Functions to handle the communication between the PC and the ESP32 and setup parameters
    #-------------------------------------------------------------------------------------------------------------#
    def send_electrode_number(self, electrode_number):
        """
        Send electrode number to ESP32

        Args:
            electrode_number: The number of electrodes used in the application.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_ELECTRODE_NUM)
        sent = self.comm.write_serial_bytes(electrode_number)
        self.number_of_electrodes = electrode_number
        

    def send_stimulation_polarity(self, polarity):
        """
        Send stimulation polarity to ESP32
        
        Args:
            polarity (int): 1 for Anodic, 0 for Cathodic.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_STIMULATION_POLARITY)
        sent = self.comm.write_serial_bytes(polarity)
        self.stimulation_polarity = polarity
        

    def send_stimulation_pulse_height(self, pulse_height):
        """
        Send stimulation pulse height to ESP32

        Args:
            pulse_height (int): The pulse height for stimulation.

        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_STIMULATION_PULSE_HEIGHT)
        sent = self.comm.write_serial_bytes(pulse_height, 2, 'little') # write in little endian format
        self.stimulation_pulse_height = pulse_height
        

    def send_stimulation_pulse_width(self, pulse_width):
        """
        Send stimulation pulse width to ESP32
        
        Args:
            pulse_width (int): The pulse width for stimulation.
        
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_STIMULATION_PULSE_WIDTH)
        sent = self.comm.write_serial_bytes(pulse_width, 2, 'little')
        self.stimulation_pulse_width = pulse_width # Update the current pulse width


    def send_sense_pulse_height(self, pulse_height):
        """
        Send sense pulse height to ESP32
        
        Args:
            pulse_height (int): The pulse height used for sensing. This should be a smaller value than the stimulation pulse height so that it does not affect the stimulation but only senses the voltage.
            
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_SENSE_PULSE_HEIGHT)
        sent = self.comm.write_serial_bytes(pulse_height)
        self.sense_pulse_height = pulse_height # Update the current sense current

    
    def send_sense_pulse_width(self, pulse_width):
        """
        Send sense pulse width to ESP32
        
        Args:
            pulse_width (int): The pulse width used for sensing. This value should be considered along with the sense pulse height to ensure that the created sense pulse does not stimulate.
        
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_SENSE_PULSE_WIDTH)
        sent = self.comm.write_serial_bytes(pulse_width)
        self.sense_pulse_width = pulse_width


    def send_channel_discharge_time(self, discharge_time):
        """
        Send channel discharge time to ESP32
        
        Args:
            discharge_time (int): The time taken to discharge the channel after stimulation.
            
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_CHANNEL_DISCHARGE_TIME)
        sent = self.comm.write_serial_bytes(discharge_time)
        self.channel_discharge_time = discharge_time

        
    def send_stimulation_frequency(self, stim_freq):
        """
        Send stimulation frequency to ESP32
        
        Args:
            stim_freq (int): The frequency for stimulation pulses.
        
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        self.comm.write_serial_bytes(PC_ESP32_STIMULATION_FREQUENCY)
        sent = self.comm.write_serial_bytes(stim_freq, 2, 'little') #write in little endian format
        self.stimulation_frequency = stim_freq


    def send_stim_pattern(self, stim_pattern):
        """
        Send stimulation pattern to ESP32
        
        Args:
            stim_pattern (list): A list of n integers(8bit representable - 0 < x <255) representing the intensity values of the n electrodes.
        
        Returns:
            bool: True if the command was successfully acknowledged by the ESP32, False otherwise.
        """
        if len(stim_pattern) != self.number_of_electrodes:
            print("Stimulation pattern length should be equal to the number of electrodes")
            return False
        
        mapped_stim_pattern = [0]*self.number_of_electrodes
        for ch in range(self.number_of_electrodes):
            mapped_stim_pattern[self.electrode_mapping[ch]] = stim_pattern[ch]

        self.comm.write_serial_bytes(PC_ESP32_STIM_PATTERN)

        for ch in range(self.number_of_electrodes):
            self.comm.write_serial_bytes(mapped_stim_pattern[ch])

    
    def get_voltage_readings(self):
        """
        Read the voltage data from the ESP32 corresponding to the number of electrodes defined in the application.
        
        Returns:
            list: A list of voltage readings from each electrode.
        """
        self.comm.write_serial_bytes(PC_ESP32_MEASURE_REQUEST)
        temp_voltages = []
        for i in range(self.number_of_electrodes):
            received_data = self.comm.read_serial_bytes(len=2, byteorder='little')  # Read the voltage data
            temp_voltages.append(received_data)

        self.voltages = [temp_voltages[self.electrode_mapping[i]] for i in range(self.number_of_electrodes)]
        
        # Clear the input buffer to avoid any stale data
        self.comm.clear_serial_input_buffer()
        return self.voltages

    def update_and_get_hv513_count(self):
        """
        Get the count of HV513s connected. If only the main controller module is used this value will be 1. Each switching module adds 8 more HV513s
        
        Returns:
            int: The number of HV513 driver chips connected to the ESP32.
        """
        self.comm.write_serial_bytes(PC_ESP32_HV513_NUM_REQUEST)
        received_data = self.comm.read_serial_bytes_with_timeout(len=1, timeout = 0.05)  # Read the count of HV513s and might need more time since the reading is averaged over multiple readings internally
        self.hv513_num = received_data

        # Clear the input buffer to avoid any stale data
        self.comm.clear_serial_input_buffer()
        return received_data

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
        if self.stimulation_pulse_height is None:
            print("Stimulation pulse height is not set")
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