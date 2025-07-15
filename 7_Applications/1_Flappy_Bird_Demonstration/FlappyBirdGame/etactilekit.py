import time
# from communication import Communication
# import keyboard


PORT_1_NAME = 'COM6'  #serial port for ET device
BAUDRATE = 921600 #115200


PC_ESP32_ELECTRODE_NUMBER          = 0xFC
PC_ESP32_PULSEWIDTH                = 0xFB
PC_ESP32_PULSE_HEIGHT              = 0xFA
PC_ESP32_PULSE_PERIOD              = 0xF8
PC_ESP32_STIMULATION_FREQUENCY     = 0xF9
PC_ESP32_POLARITY_CHANGE           = 0xFD
PC_ESP32_STIMULATION_PULSE_HEIGHT  = 0xF9

PC_ESP32_STIM_PATTERN              = 0xFF

PC_ESP32_MEASURE_REQUEST           = 0xFE
PC_ESP32_HV513_NUM_REQUEST         = 0xF7
ESP32_PC_RECEIVE_FINISHED          = 0xFE
ESP32_PC_MEASURE_RESULT            = 0xFF
NUMBER_OF_ELECTRODES = 64


#--------------------------------------------Function to set the stimulation pattern--------------------------------------------
# serial_port_1 = connect_ET_device()

# send_pulse_width(serial_port_1,100)
# send_sense_current(serial_port_1,400 )

# stim_pattern        = [00]*64
# stim_pattern[32]    = 800
# stim_pattern[33]    = 800

# send_stim_pattern(serial_port_1,stim_pattern)

# while(True):
#     print(get_voltage_data(serial_port_1))

# def ET_calibration(ET_device):
#     stim_value = 0
#     stim_pulse_width = 100
#     sense_current = 400
#     sense_pulse_width = 100 #this is not the pulse_width of sense pulse,still stim pulse's pulse width

#     def adjust_values(ET_device,Pulse_Width,stim_current,stim_pattern):
#         if keyboard.is_pressed('up'):
#             stim_current += 10
#             stim_current = min(stim_current, 1200)
#             print(f"Stim current increased to {stim_current}")
#             stim_pattern[32] = stim_current
#             stim_pattern[33] = stim_current
#             send_stim_pattern(ET_device, stim_pattern)
#             send_sense_current(ET_device,stim_current)
#             time.sleep(0.1)
#         elif keyboard.is_pressed('down'):
#             stim_current -= 10
#             stim_current = max(stim_current, 0)
#             print(f"Stim current decreased to {stim_current}")
#             stim_pattern[32] = stim_current
#             stim_pattern[33] = stim_current
#             send_stim_pattern(ET_device, stim_pattern)
#             send_sense_current(ET_device,stim_current)
#             time.sleep(0.1)
#         elif keyboard.is_pressed('left'):
#             Pulse_Width -= 10
#             Pulse_Width = max(Pulse_Width, 0)
#             print(f"Pulse Width decreased to {Pulse_Width}")
#             send_pulse_width(ET_device, Pulse_Width)
#             time.sleep(0.1)
#         elif keyboard.is_pressed('right'):
#             Pulse_Width += 10
#             Pulse_Width = min(Pulse_Width, 200)
#             print(f"Pulse Width increased to {Pulse_Width}")
#             send_pulse_width(ET_device, Pulse_Width)
#             time.sleep(0.1)
#         elif keyboard.is_pressed('n'):
#             raise KeyboardInterrupt
#         return(Pulse_Width,stim_current,stim_pattern)
    
#     print("Started ET Calibration.")
#     print("Started ET Calibration - Absolute Threshold Calibration.")
    
#     Pulse_Width = sense_pulse_width
#     stim_current = sense_current
#     stim_pattern = [0]*64
#     stim_pattern[32],stim_pattern[33] = sense_current,sense_current
#     send_pulse_width(ET_device, Pulse_Width)
#     send_stim_pattern(ET_device, stim_pattern)
#     send_sense_current(ET_device,sense_current)
        
#     try:
#         while True:
#             Pulse_Width,stim_current,stim_pattern = adjust_values(ET_device,Pulse_Width,stim_current,stim_pattern)
#     except KeyboardInterrupt:
#         sense_current = stim_current
#         sense_pulse_width = Pulse_Width
#         print("Absolute Threshold Calibration Finished.")

#     time.sleep(3)
#     print("Started ET Calibration - Pain Threshold Calibration.")
#     stim_current = stim_current+200
#     stim_pattern = [0]*64
#     stim_pattern[32],stim_pattern[33] = sense_current+200,sense_current+200
#     send_pulse_width(ET_device, sense_pulse_width)
#     send_stim_pattern(ET_device, stim_pattern)
#     send_sense_current(ET_device,sense_current)

#     try:
#         while True:
#             Pulse_Width,stim_current,stim_pattern = adjust_values(ET_device,Pulse_Width,stim_current,stim_pattern)
#     except KeyboardInterrupt:
#         stim_value = stim_current
#         stim_pulse_width = Pulse_Width
#         print("Pain Threshold Calibration Finished.")

#     return (stim_value,stim_pulse_width,sense_current,sense_pulse_width)

class ETactileKit:
    def __init__(self, communication):
        self.comm = communication  # Communication object for serial communication tasks

        # Current parameters
        # self.number_of_electrodes = None
        self.number_of_electrodes = 8
        self.pulse_width = None
        self.pulse_period = None
        self.stimulation_frequency = None
        self.sense_current = None

    def send_pulse_width(self, pulse_width):
        '''Send pulse width to ESP32'''
        self.comm.write_serial_bytes(PC_ESP32_PULSEWIDTH)
        sent = self.comm.write_serial_bytes(pulse_width)
        self.pulse_width = pulse_width # Update the current pulse width
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False
    
    def send_pulse_height(self, pulse_height):
        '''Send pulse height to ESP32'''
        self.comm.write_serial_bytes(PC_ESP32_PULSE_HEIGHT)
        sent = self.comm.write_serial_bytes(pulse_height)
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False
        
    def send_pulse_period(self, pulse_period):
        '''Send pulse period to ESP32'''
        self.comm.write_serial_bytes(PC_ESP32_PULSE_PERIOD)
        sent = self.comm.write_serial_bytes(pulse_period)
        self.pulse_period = pulse_period # Update the current pulse period
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False

    def send_stimulation_frequency(self, stim_freq):
        '''Send stimulation frequency to ESP32'''
        self.comm.write_serial_bytes(PC_ESP32_STIMULATION_FREQUENCY)
        sent = self.comm.write_serial_bytes(stim_freq)
        self.stimulation_frequency = stim_freq
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False
        
    def send_polarity_change(self):
        '''Send polarity change command to ESP32
           This function is used to change the polarity of the stimulation pattern to Anodic or Cathodic
           The ESP32 will toggle the polarity of the stimulation pattern and return a success message'''
        self.comm.write_serial_bytes(PC_ESP32_POLARITY_CHANGE)
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False
    
    def send_sense_current(self, sense_current):
        '''Send sense current to ESP32
           Sense current is the current used for sensing the voltage of the electrodes
           The ESP32 will set the sense current and return a success message'''
        self.comm.write_serial_bytes(PC_ESP32_STIMULATION_PULSE_HEIGHT)
        sent = self.comm.write_serial_bytes(sense_current)
        self.sense_current = sense_current # Update the current sense current
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False
    
    def send_electrode_number(self, electrode_number):
        '''Send electrode number to ESP32
           The electrode number is the number of the electrodes used in the application
           The ESP32 will set the electrode number and return a success message'''
        self.comm.write_serial_bytes(PC_ESP32_ELECTRODE_NUMBER)
        sent = self.comm.write_serial_bytes(electrode_number)
        self.number_of_electrodes = electrode_number
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False

    def send_stim_pattern(self, stim_pattern):
        '''Send stimulation pattern to ESP32
           The stimulation pattern is a list of n bytes representing the intensity values of the n electrodes
           The ESP32 will set the stimulation pattern and return a success message'''
        if len(stim_pattern) != self.number_of_electrodes:
            print("Stimulation pattern length should be equal to the number of electrodes")
            return False
        self.comm.write_serial_bytes(PC_ESP32_STIM_PATTERN)
        for ch in range(self.number_of_electrodes):
            self.comm.write_serial_bytes(stim_pattern[ch])
        rcv = self.comm.read_serial_bytes_with_timeout()
        if int.from_bytes(rcv) == ESP32_PC_RECEIVE_FINISHED:
            return True
        else:
            return False
    
    def get_voltage_readings(self):
        '''Get voltage data from ESP32
           The ESP32 will send the voltage data of the electrodes to the PC'''
        self.comm.write_serial_bytes(PC_ESP32_MEASURE_REQUEST)
        voltages = []
        time.sleep(0.1)
        for i in range(self.number_of_electrodes):
            received_data = self.comm.read_serial_bytes_with_timeout()
            voltages.append(int.from_bytes(received_data,byteorder='big'))
        return voltages

    def get_hv513_count(self):
        '''Get the count of HV513s connected to the ESP32
           The ESP32 will send the count of HV513s to the PC'''
        self.comm.write_serial_bytes(PC_ESP32_HV513_NUM_REQUEST)
        received_data = self.comm.read_serial_bytes_with_timeout()
        return int.from_bytes(received_data,byteorder='big')      


# # Create a Communication object and connect to the serial port for testing
# comm = Communication(PORT_1_NAME, BAUDRATE)
# comm.connect()

# etactilekit = ETactileKit(comm)

# x = etactilekit.send_pulse_width(50)
# print("Pulse width status:", x)
# x = etactilekit.send_pulse_height(20)
# print("Pulse height status:", x)

# x = etactilekit.send_electrode_number(64)
# print("Electrode number status:", x)

# on_pattern  = [1]*64
# off_pattern = [0]*64

# #write the stimulation current
# # etactilekit.send_sense_current(10)
# time.sleep(1)

# hv_513_count = etactilekit.get_hv513_count()
# print("HV513 count:", hv_513_count)

# while True:   
#     etactilekit.send_stim_pattern(off_pattern)
#     # voltages = etactilekit.get_voltage_readings()
#     # print(voltages)
    
#     time.sleep(0.5)
#     etactilekit.send_stim_pattern(on_pattern)
#     time.sleep(0.5)
    
