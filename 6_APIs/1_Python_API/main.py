from api.etactilekit import ETactileKit, ETactileKitBLE
from api.pattern_reader import PatternReader
import time
import asyncio

# --- Configuration Parameters for BLE Communication ---
DEVICE_NAME = "eTactileKit_BLE"  # BLE device name

async def run_test_ble():
    # Initialize the EtactileKit object
    etactilekit = ETactileKitBLE(device_name=DEVICE_NAME)

    await etactilekit.connect_etactilekit()

    ''' Setting up etactileKit. Please follow the below steps:
    1. Set the electrode number
    2. Set the mapping function - this should be updated
    '''
    electrode_number = 32
    pulse_width = 100
    amplitude = 250
    frequency = 50

    electrode_mapping = [x for x in range(electrode_number)]

    etactilekit.set_electrode_mapping(electrode_mapping)

    await etactilekit.send_electrode_number(electrode_number)
    
    await etactilekit.send_stimulation_pulse_height(amplitude)
    
    await etactilekit.send_stimulation_pulse_width(pulse_width)
    
    await etactilekit.send_sense_pulse_height(0)
    
    await etactilekit.send_sense_pulse_width(0)
    
    await etactilekit.send_channel_discharge_time(100)
    
    await etactilekit.send_stimulation_frequency(frequency)
    
    hv_513_count = await etactilekit.update_and_get_hv513_count()
    print("HV513 count:", hv_513_count)
    print("ETactileKit setup complete.")

    # # Setting up the stimulation pattern
    # PATTERN_FILE = "./example_patterns/test_pattern.json" # Path to the JSON file containing the patterns
    # pattern_reader  = PatternReader()
    # pattern_reader.load_file(PATTERN_FILE)


    # while True:
    #     pattern_info = pattern_reader.next_pattern()
    #     pattern = pattern_info["pattern"]
    #     on_time = pattern_info["on_time"]
    #     off_time = pattern_info["off_time"]
    #     frequency = pattern_info["frequency"]
    #     stim_mode = pattern_info["stim_mode"]
    #     off_pattern = [0]*electrode_number

    #     await etactilekit.send_stimulation_frequency(frequency)
    #     await etactilekit.send_stimulation_polarity(stim_mode)
    #     await etactilekit.send_stim_pattern(pattern)
    #     await asyncio.sleep(on_time/1000) # Convert to seconds
    #     print("Pattern sent:", pattern)
    #     await etactilekit.send_stim_pattern(off_pattern)
    #     await asyncio.sleep(off_time/1000) # Convert to seconds

    on_pattern  = [1]*electrode_number
    off_pattern = [0]*electrode_number
    await asyncio.sleep(1)

    # Send the on and off pattern alternatively every X second

    delay_interval = 0.5
    last_pattern_sent_time = time.time()
    last_voltage_read_time = last_pattern_sent_time

    flag = 0
    while True:
        current_time = time.time()
        if current_time - last_pattern_sent_time >= delay_interval: # send pattern every delay_interval seconds
            await etactilekit.send_stim_pattern(on_pattern if flag else off_pattern)
            flag = 1 - flag
            last_pattern_sent_time = current_time

        # if current_time - last_voltage_read_time >= 0.1: # read voltage every 100 ms
        #     voltages = await etactilekit.get_voltage_readings()
        #     print(voltages[-8:-1])  # Print last 8 voltage readings
        #     last_voltage_read_time = current_time


# --- Configuration Parameters for Serial Communication ---
PORT_1_NAME = 'COM16'  #serial port for ET device
BAUDRATE = 921600 #115200
TIMEOUT = 0.005 # Serial read timeout in seconds

# --- Configuration Parameters for Wifi Communication ---
ESP_IP = "192.168.4.1"
ESP_PORT = 8080
TIMEOUT = 0.10 # Serial read timeout in seconds
'''
WIFI_SSID ----------->eTactileKit_AP
WIFI_PASSWORD ------->etactile@al
'''

def run_test_serial_wifi(comm_mode = "serial"):# comm_mode can be "serial" or "wifi"
    # Initialize the EtactileKit object
    if comm_mode == "serial":
        etactilekit = ETactileKit()
        etactilekit.connect_etactilekit_to_serial(PORT_1_NAME, BAUDRATE, TIMEOUT)
    elif comm_mode == "wifi":
        etactilekit = ETactileKit()
        etactilekit.connect_etactilekit_to_wifi(ESP_IP, ESP_PORT, TIMEOUT)

    ''' Setting up etactileKit. Please follow the below steps:
    1. Set the electrode number
    2. Set the mapping function - this should be updated
    '''
    electrode_number = 32
    pulse_width = 100
    amplitude = 220
    frequency = 50

    electrode_mapping = [x for x in range(electrode_number)]

    etactilekit.set_electrode_mapping(electrode_mapping)

    etactilekit.send_electrode_number(electrode_number)
    
    etactilekit.send_stimulation_pulse_height(amplitude)
    
    etactilekit.send_stimulation_pulse_width(pulse_width)
    
    etactilekit.send_sense_pulse_height(0)
    
    etactilekit.send_sense_pulse_width(0)
    
    etactilekit.send_channel_discharge_time(50)
    
    etactilekit.send_stimulation_frequency(frequency)
    
    hv_513_count = etactilekit.update_and_get_hv513_count()
    print("HV513 count:", hv_513_count)
    print("ETactileKit setup complete.")

    # # Setting up the stimulation pattern
    # PATTERN_FILE = "./example_patterns/test_pattern.json" # Path to the JSON file containing the patterns
    # pattern_reader  = PatternReader()
    # pattern_reader.load_file(PATTERN_FILE)


    # while True:
    #     pattern_info = pattern_reader.next_pattern()
    #     pattern = pattern_info["pattern"]
    #     on_time = pattern_info["on_time"]
    #     off_time = pattern_info["off_time"]
    #     frequency = pattern_info["frequency"]
    #     stim_mode = pattern_info["stim_mode"]
    #     off_pattern = [0]*electrode_number

    #     etactilekit.send_stimulation_frequency(frequency)
    #     etactilekit.send_stimulation_polarity(stim_mode)
    #     etactilekit.send_stim_pattern(pattern)
    #     time.sleep(on_time/1000) # Convert to seconds
    #     print("Pattern sent:", pattern)
    #     etactilekit.send_stim_pattern(off_pattern)
    #     time.sleep(off_time/1000) # Convert to seconds

    on_pattern  = [1]*electrode_number
    off_pattern = [0]*electrode_number
    time.sleep(1)

    # Send the on and off pattern alternatively every X second

    delay_interval = 0.5
    last_pattern_sent_time = time.time()
    last_voltage_read_time = last_pattern_sent_time

    flag = 0
    while True:
        current_time = time.time()
        if current_time - last_pattern_sent_time >= delay_interval: # send pattern every delay_interval seconds
            etactilekit.send_stim_pattern(on_pattern if flag else off_pattern)
            flag = 1 - flag
            last_pattern_sent_time = current_time

        # if current_time - last_voltage_read_time >= 0.1: # read voltage every 100 ms
        #     voltages = etactilekit.get_voltage_readings()
        #     print(voltages[-8:-1])  # Print last 8 voltage readings
        #     last_voltage_read_time = current_time

if __name__ == "__main__":
    # asyncio.run(run_test_ble())
    # run_test_serial_wifi("wifi")
    run_test_serial_wifi("serial")