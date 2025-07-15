import serial
import time

class Communication:
    """
    A class to manage serial communication using the pySerial library.
    """
    def __init__(self, port_name, baudrate, timeout = 0.02):
        """
        Initialize the Communication object with serial port parameters.

        Args:
            port_name (str): The name of the serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux).
            baudrate (int): The communication speed in baud.
            timeout (float, optional): The default timeout for serial read operations. Defaults to 0.02.
        """

        self.port_name = port_name
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None

    def connect(self):
        """
        Attempt to establish a connection to the serial port.

        This method continuously tries to connect to the specified serial port. 
        If it cannot connect for more than 2 seconds at a time, 
        it will print a warning message and then keep trying.

        Returns:
            bool: True once the serial connection is successfully established.
        """
        prev = time.time()
        SETUP = False
        while(not SETUP):
            try:
                self.serial_port = serial.Serial(
                    self.port_name,
                    self.baudrate,
                    timeout = self.timeout)
            except:
                if(time.time()-prev > 2):
                    print("No serial detected. Please check your connections")
                    prev = time.time()
            if(self.serial_port is not None):
                SETUP = True    
                print(f"Connected to Serial device at {self.port_name} with {self.baudrate} baud rate")
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                return True
    
    def read_serial_bytes_with_timeout(self, timeout=0.005):
        """
        Read a single byte from the serial port using a temporary timeout setting.

        Args:
            timeout (float, optional): The temporary read timeout for this read operation.
                Defaults to 0.005.

        Returns:
            int: Integer representation of the single byte read. If no data is received 
            within the given timeout, the result may be None or 0 (depending on the OS).
        """
        received_data = None
        self.serial_port.timeout = timeout
        received_data = int.from_bytes(self.serial_port.read(1), byteorder='big')
        self.serial_port.timeout = self.timeout #reset the timeout
        return received_data
    
    def read_serial_bytes(self,len=1):
        """
        Read a specified number of bytes from the serial port.

        Args:
            length (int, optional): The number of bytes to read. Defaults to 1.

        Returns:
            int: Integer representation of the bytes read, or None if no data is received.
        """
        received_data = None
        received_data = int.from_bytes(self.serial_port.read(len), byteorder='big')
        return received_data

    def read_serial_string(self):
        """
        Read a line from the serial port as a UTF-8 encoded string, stripping trailing whitespace.

        Returns:
            str: The UTF-8 decoded string read from the serial port.
        """
        received_data = None
        received_data = self.serial_port.readline().decode('utf-8').strip()
        return received_data
    
    def write_serial_bytes(self, command):
        """
        Write a single-byte command to the serial port.

        Args:
            command (int): The integer value representing the byte to be sent.
        """
        self.serial_port.write(bytes([command]))

    def clear_serial_input_buffer(self):
        """
        Clear the input buffer of the serial port.
        """
        self.serial_port.reset_input_buffer()
    
    def clear_serial_output_buffer(self):
        """
        Clear the output buffer of the serial port.
        """
        self.serial_port.reset_output_buffer()
    
    def disconnect(self):
        """
        Close the serial connection and release the resources.
        """
        self.serial_port.close()
        self.serial_port = None
        print("Serial port disconnected")