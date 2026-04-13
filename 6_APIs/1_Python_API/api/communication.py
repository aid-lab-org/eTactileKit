#-------------------------------------------------------------------------------
# BLE Communication Class
#-------------------------------------------------------------------------------
import asyncio
import struct
from bleak import BleakClient, BleakScanner
from asyncio import Queue
import time

# UUIDs
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
RX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E" # Write to this (Send to ESP)
TX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" # Subscribe to this (Read from ESP)


class CommunicationBLE:
    """
    A class to manage ble communication.
    """
    def __init__(self, device_name="eTactileKit_BLE"):
        """
        Initialize the Communication object with serial port parameters.
        
        Args:
            device_name (str): The name of the BLE device to connect to. Defaults to "eTactileKit_BLE".
        """
        self.device_name = device_name
        self.client = None
        self.rx_buffer = Queue()
        self.connected = False

    async def connect(self):
        """
        Attempt to establish a BLE connection to the device.
        Returns:
            bool: True once the BLE connection is successfully established.
        """

        print(f"Scanning for {self.device_name}...")
        device = await BleakScanner.find_device_by_name(self.device_name)

        if not device:
            print("Device not found.")
            return False

        self.client = BleakClient(device)
        await self.client.connect()
        self.connected = self.client.is_connected
        print(f"Connected: {self.connected}")

        # Start receiving data
        await self.client.start_notify(TX_UUID, self.notification_handler)
        return True
    
    async def disconnect(self):
        if self.client:
            await self.client.stop_notify(TX_UUID)
            await self.client.disconnect()
            print("Disconnected")
    
    # Callback when data arrives from ESP32
    def notification_handler(self, sender, data):
        # Add bytes to the thread-safe queue
        for byte in data:
            self.rx_buffer.put_nowait(byte)

    # --- Read Functions ---
    async def read_bytes_with_timeout(self, num_bytes=1, timeout=0.010, byteorder='little'):
        """
        Read a specified number of bytes from the BLE buffer with timeout.

        Args:
            num_bytes (int, optional): The number of bytes to read. Defaults to 1.
            timeout (float, optional): The read timeout in seconds. Defaults to 0.010.
            byteorder (str): The byte order ('little' or 'big'). Defaults to 'little'.

        Returns:
            int: Integer representation of the bytes read. Returns None if timeout occurs.
        """
        try:
            received_data = 0
            for i in range(num_bytes):
                byte = await asyncio.wait_for(self.rx_buffer.get(), timeout=timeout)
                if byteorder == 'little':
                    received_data |= (byte << (8 * i))
                else:
                    received_data |= (byte << (8 * (num_bytes - 1 - i)))
            return received_data
        except asyncio.TimeoutError:
            return None
    
    async def read_bytes(self, num_bytes=1, byteorder='little'):
        """
        Read a specified number of bytes from the BLE buffer.

        Args:
            num_bytes (int, optional): The number of bytes to read. Defaults to 1.
            byteorder (str): The byte order ('little' or 'big'). Defaults to 'little'.

        Returns:
            int: Integer representation of the bytes read.
        """
        received_data = 0
        for i in range(num_bytes):
            byte = await self.rx_buffer.get_nowait()
            if byteorder == 'little':
                received_data |= (byte << (8 * i))
            else:
                received_data |= (byte << (8 * (num_bytes - 1 - i)))
        return received_data
    
    # --- Write Functions ---
    async def write_bytes(self, val, num_bytes=1, byteorder='little'):
        """
        Write the given number of bytes in the specified order via BLE.

        Args:
            val (int): The integer value representing the bytes to be sent.
            num_bytes (int): The number of bytes to write. Defaults to 1.
            byteorder (str): The byte order ('little' or 'big'). Defaults to 'little'.
        """
        if not self.connected: return
        data = struct.pack(f'<{"B" * num_bytes}' if byteorder == 'little' else f'>{"B" * num_bytes}', *[val >> (8*i) & 0xFF for i in range(num_bytes)])
        await self.client.write_gatt_char(RX_UUID, data, response=False)

    def isDataAvailable(self):
        return self.rx_buffer.qsize()
    
    def clear_input_buffer(self):
        """
        Clear the input buffer of BLE.
        """

        self.rx_buffer = Queue()


#-------------------------------------------------------------------------------
# Serial Communication Class
#-------------------------------------------------------------------------------
import serial
import time

class CommunicationSerial:
    """
    A class to manage serial communication using the pySerial library.
    """
    def __init__(self, port_name, baudrate, timeout=0.02):
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
    
    def disconnect(self):
        """
        Close the serial connection and release the resources.
        """
        self.serial_port.close()
        self.serial_port = None
        print("Serial port disconnected")

    def read_bytes_with_timeout(self, num_bytes = 1, byteorder='little', timeout=0.010):
        """
        Read the specified number of bytes.

        Args:
            timeout (float, optional): The temporary read timeout for this read operation.
                Defaults to 0.005.

        Returns:
            int: Integer representation of the single byte read. If no data is received 
            within the given timeout, the result may be None or 0 (depending on the OS).
        """
        received_data = None
        self.serial_port.timeout = timeout
        received_data = int.from_bytes(self.serial_port.read(num_bytes), byteorder=byteorder)
        self.serial_port.timeout = self.timeout #reset the timeout
        return received_data
    
    def read_bytes(self, num_bytes=1, byteorder='little'):
        """
        Read a specified number of bytes from the serial port.

        Args:
            length (int, optional): The number of bytes to read. Defaults to 1.

        Returns:
            int: Integer representation of the bytes read, or None if no data is received.
        """
        received_data = None
        received_data = int.from_bytes(self.serial_port.read(num_bytes), byteorder=byteorder)
        return received_data

    def read_string(self):
        """
        Read a line from the serial port as a UTF-8 encoded string, stripping trailing whitespace.

        Returns:
            str: The UTF-8 decoded string read from the serial port.
        """
        received_data = None
        received_data = self.serial_port.readline().decode('utf-8').strip()
        return received_data

    def write_bytes(self, val, num_bytes=1, byteorder='little'):
        """
        Write a the given number of bytes in the specified order.

        Args:
            val (int): The integer value representing the byte to be sent.
        """
        self.serial_port.write(int.to_bytes(val, num_bytes, byteorder))
        return True

    def clear_input_buffer(self):
        """
        Clear the input buffer of the serial port.
        """
        self.serial_port.reset_input_buffer()
    
    def clear_output_buffer(self):
        """
        Clear the output buffer of the serial port.
        """
        self.serial_port.reset_output_buffer()

#-------------------------------------------------------------------------------
# WIFI Communication Class
#-------------------------------------------------------------------------------
import socket
import struct
import time

class CommunicationWiFi:
    """
    A class to manage serial communication using the pySerial library.
    """
    def __init__(self, ip, port, timeout=0.02):
        """
        Initialize the Communication object with serial port parameters.

        Args:
            port_name (str): The name of the serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux).
            baudrate (int): The communication speed in baud.
            timeout (float, optional): The default timeout for serial read operations. Defaults to 0.02.
        """
        self.ip = ip
        self.port = port
        self.sock = None
        self.timeout = timeout
        self.connected = False
        # Internal buffer to store partial packets received from TCP
        # self.rx_buffer = bytearray()

    def connect(self):
        """
        Attempt to establish a connection to the WiFi device.

        This method continuously tries to connect to the specified WiFi device. 
        If it cannot connect for more than 2 seconds at a time, 
        it will print a warning message and then keep trying.

        Returns:
            bool: True once the serial connection is successfully established.
        """
        try:
            print(f"Connecting to {self.ip}:{self.port}...")
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5) # 5 second timeout for connection
            self.sock.connect((self.ip, self.port))
            self.sock.settimeout(self.timeout) # Remove timeout for blocking operations (or keep it if you prefer)
            self.connected = True
            self.sock
            print("Connected via WiFi!")
            return True
        except Exception as e:
            print(f"Connection Failed: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """
        Close the serial connection and release the resources.
        """
        if self.sock:
            self.sock.close()
        self.connected = False
        print("WiFi connection disconnected")
    
    # def _fill_buffer(self, required_bytes):
    #     """
    #     Reads from socket until rx_buffer has enough data.
    #     Returns True if successful, False if connection broke.
    #     """
    #     while len(self.rx_buffer) < required_bytes:
    #         try:
    #             # Receive up to 1024 bytes
    #             chunk = self.sock.recv(1024)
    #             if not chunk: 
    #                 # Empty bytes means the server closed the connection
    #                 self.connected = False
    #                 return False
    #             self.rx_buffer.extend(chunk)
    #         except socket.error as e:
    #             print(f"Socket Error: {e}")
    #             self.connected = False
    #             return False
    #     return True
    
    def read_bytes_with_timeout(self, num_bytes = 1, byteorder='little', timeout=0.010):
        """
        Read the specified number of bytes.

        Args:
            timeout (float, optional): The temporary read timeout for this read operation.
                Defaults to 0.005.

        Returns:
            int: Integer representation of the single byte read. If no data is received 
            within the given timeout, the result may be None or 0 (depending on the OS).
        """
        received_data = None
        self.sock.settimeout(timeout)
        received_data = int.from_bytes(self.sock.recv(num_bytes), byteorder=byteorder)
        self.sock.settimeout(self.timeout) #reset the timeout
        return received_data
    
    def read_bytes(self, num_bytes=1, byteorder='little'):
        """
        Read a specified number of bytes from the serial port.

        Args:
            length (int, optional): The number of bytes to read. Defaults to 1.

        Returns:
            int: Integer representation of the bytes read, or None if no data is received.
        """
        received_data = None
        received_data = int.from_bytes(self.sock.recv(num_bytes), byteorder=byteorder)
        return received_data

    def write_bytes(self, val, num_bytes=1, byteorder='little'):
        """
        Write a the given number of bytes in the specified order.

        Args:
            val (int): The integer value representing the byte to be sent.
        """
        if not self.connected: return
        try:
            self.sock.sendall(int.to_bytes(val, num_bytes, byteorder))
        except socket.error as e:
            print(f"Socket Error on send: {e}")
            self.connected = False

    def clear_input_buffer(self):
        """
        Clear the input buffer of the serial port.
        """
        try:
            self.sock.setblocking(False)
            while True:
                self.sock.recv(4096)
        except BlockingIOError:
            pass
        finally:
            self.sock.setblocking(True)
        pass
    