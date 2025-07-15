import serial
import time

class Communication:
    def __init__(self, port_name, baudrate):
        self.port_name = port_name
        self.baudrate = baudrate
        self.serial_port = None

    def connect(self):
        # Connect to the serial port
        prev = time.time()
        SETUP = False
        while(not SETUP):
            try:
                self.serial_port = serial.Serial(self.port_name, self.baudrate, timeout=1)
            except:
                if(time.time()-prev > 2):
                    print("No serial detected. Please check your connections")
                    prev = time.time()
            if(self.serial_port is not None):
                SETUP = True    
                print(f"Connected to Serial device at {self.port_name} with {self.baudrate} baud rate")
                self.serial_port.flushInput()#flush the serial port to clear any old data
                return True
    
    def read_serial_bytes_with_timeout(self, timeout=0.005):
        received_data = None
        start_time = time.time()
        while(time.time()-start_time < timeout):
            if(self.serial_port.in_waiting > 0):
                received_data = self.serial_port.read(1)
                break
        return received_data
    
    def read_serial_bytes(self,len=1):
        received_data = None
        if(self.serial_port.in_waiting > 0):
            received_data = self.serial_port.read(len)
        return received_data
    
    def read_serial_string(self):
        received_data = None
        if(self.serial_port.in_waiting > 0):
            received_data = self.serial_port.readline().decode('utf-8').strip()
        return received_data
    
    def write_serial_bytes(self, command):
        self.serial_port.write(bytes([command]))

    def clear_serial_input_buffer(self):
        self.serial_port.reset_input_buffer()
    
    def clear_serial_output_buffer(self):
        self.serial_port.reset_output_buffer()
    
    def disconnect(self):
        self.serial_port.close()
        self.serial_port = None
        print("Serial port disconnected")
