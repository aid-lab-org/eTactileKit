from api.etactilekit import ETactileKit#, ETactileKitBLE
import time
import sys
import platform
import threading

# --- Platform-specific keyboard imports ---
_IS_WINDOWS = platform.system() == 'Windows'
if _IS_WINDOWS:
    import msvcrt
else:
    import tty
    import termios
    import select

# --- Configuration Parameters for Serial Communication ---
PORT_1_NAME = 'COM12'  # serial port for ET device
BAUDRATE    = 921600   # 115200
TIMEOUT     = 0.005    # Serial read timeout in seconds

# --- Amplitude Control ---
AMPLITUDE_STEP = 5
AMPLITUDE_MIN  = 0
AMPLITUDE_MAX  = 450

amplitude = 0  # updated by keyboard thread, read by main loop


def _update_amplitude(delta):
    """Clamp and update the shared amplitude variable."""
    global amplitude
    amplitude = max(AMPLITUDE_MIN, min(AMPLITUDE_MAX, amplitude + delta))
    sys.stdout.write(f"\rAmplitude: {amplitude}   \n")
    sys.stdout.flush()


def _keyboard_listener_windows():
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key in (b'\x00', b'\xe0'):   # special-key prefix
                key = msvcrt.getch()
                if key == b'H':             # UP arrow
                    _update_amplitude(+AMPLITUDE_STEP)
                elif key == b'P':           # DOWN arrow
                    _update_amplitude(-AMPLITUDE_STEP)
            elif key in (b'q', b'Q'):
                print("Quitting...")
                import os; os._exit(0)


def _keyboard_listener_unix():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            if select.select([sys.stdin], [], [], 0.01)[0]:
                key = sys.stdin.read(1)
                if key in ('w', 'W'):                  # W for UP
                    _update_amplitude(+AMPLITUDE_STEP)
                elif key in ('s', 'S'):                  # S for DOWN
                    _update_amplitude(-AMPLITUDE_STEP)
                if key == ('\x1b'):
                    seq = sys.stdin.read(2)  # Read the next two chars for arrow keys
                    if seq == '[A':             # UP arrow
                        _update_amplitude(+AMPLITUDE_STEP)
                    elif seq == '[B':             # DOWN arrow
                        _update_amplitude(-AMPLITUDE_STEP)
                elif key in ('q', 'Q', '\x03'):            # q, Q, or Ctrl+C
                    sys.stdout.write("\r\nQuitting...\r\n")
                    sys.stdout.flush()
                    break
                sys.stdout.write("\r")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        import os; os._exit(0)


def keyboard_listener():
    """Listen for UP/DOWN arrow keys to adjust amplitude (no serial writes)."""
    print("Amplitude control: UP arrow (+5) | DOWN arrow (-5) | Q to quit")
    print(f"Amplitude: {amplitude}")
    if _IS_WINDOWS:
        _keyboard_listener_windows()
    else:
        _keyboard_listener_unix()


def run_test_serial():
    # Initialize the EtactileKit object
    etactilekit = ETactileKit()
    etactilekit.connect_etactilekit_to_serial(PORT_1_NAME, BAUDRATE, TIMEOUT)

    ''' Setting up etactileKit. Please follow the below steps:
    1. Set the electrode number
    2. Set the mapping function - this should be updated
    '''
    electrode_number = 32
    pulse_width = 100
    frequency = 50

    electrode_mapping = [x for x in range(electrode_number)]

    etactilekit.set_electrode_mapping(electrode_mapping)

    etactilekit.send_electrode_number(electrode_number)

    etactilekit.send_stimulation_mode(1) # 0 for monophasic, 1 for biphasic

    etactilekit.send_stimulation_pulse_width(pulse_width)

    etactilekit.send_sense_pulse_height(0)

    etactilekit.send_sense_pulse_width(0)

    etactilekit.send_channel_discharge_time(50)

    etactilekit.send_stimulation_frequency(frequency)

    hv_513_count = etactilekit.update_and_get_hv513_count(timeout=0.5)
    print("HV513 count:", hv_513_count)
    print("ETactileKit setup complete.")

    recv = etactilekit.sync_check(num_bytes=1)  # Optional: verify communication is working after setup
    print("Sync check response (Electrode Number):", recv)

    # Start keyboard listener thread (serial writes stay on the main thread)
    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()


    on_pattern  = [amplitude]*electrode_number
    off_pattern = [0]*electrode_number
    time.sleep(1)

    # Send the on and off pattern alternatively every X second
    delay_interval = 0.5
    # voltage_read_interval = 0.4
    last_pattern_sent_time = time.time()
    # last_voltage_read_time = last_pattern_sent_time

    last_sent_amplitude = amplitude
    flag = 0
    while True:
        current_time = time.time()
        if current_time - last_pattern_sent_time >= delay_interval: # send pattern every delay_interval seconds

            if amplitude != last_sent_amplitude:
                on_pattern = [amplitude]*electrode_number
                last_sent_amplitude = amplitude   

            etactilekit.send_stim_pattern(on_pattern if flag else off_pattern)
            flag = 1 - flag
            last_pattern_sent_time = current_time

        # if current_time - last_voltage_read_time >= voltage_read_interval:
        #     voltages = etactilekit.get_voltage_readings(timeout=0.05)  # Read voltage data every voltage_read_interval seconds
        #     if voltages is not None:
        #         print(voltages[-8:])  # Print last 8 voltage readings
        #     last_voltage_read_time = current_time

if __name__ == "__main__":
    run_test_serial()