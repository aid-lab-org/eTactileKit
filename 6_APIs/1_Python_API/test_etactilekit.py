from api.etactilekit import ETactileKit
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

# --- Connection ---
# The kit accepts USB serial and WiFi at the same time; the first host to connect owns it until it
# disconnects. MODE picks the link: "serial" or "wifi".
MODE              = "wifi"   # "serial" or "wifi"
SERIAL_PORT       = "COM12"    # e.g. 'COM13' or '/dev/ttyACM0'; None = the kit found on USB
TARGET_DEVICE_ID  = "604FE0"    # The kit's 6-hex ID (sticker, or "python -m api.discovery"), on USB or WiFi; None = the only kit found
WIFI_HOST         = None    # WiFi: fixed address instead of discovery, e.g. "192.168.4.1" when joined to the kit's own AP
                            #       (SSID "eTactileKit_<ID>", password "etactile@al")

# --- Stimulation setup ---
ELECTRODE_NUMBER  = 32
PULSE_WIDTH       = 100     # us
FREQUENCY         = 50      # Hz
STIMULATION_MODE  = 0       # 0 for monophasic, 1 for biphasic

# --- Amplitude Control ---
AMPLITUDE_STEP = 5
AMPLITUDE_MIN  = 0
AMPLITUDE_MAX  = 450

amplitude = 0  # updated by keyboard thread, read by main loop
quit_requested = threading.Event()  # set by the keyboard thread; the main loop then turns everything off


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
                quit_requested.set()
                return


def _keyboard_listener_unix():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            if select.select([sys.stdin], [], [], 0.01)[0]:
                key = sys.stdin.read(1)
                if key in ('w', 'W'):                      # W for UP
                    _update_amplitude(+AMPLITUDE_STEP)
                elif key in ('s', 'S'):                    # S for DOWN
                    _update_amplitude(-AMPLITUDE_STEP)
                if key == ('\x1b'):
                    seq = sys.stdin.read(2)                # Read the next two chars for arrow keys
                    if seq == '[A':                        # UP arrow
                        _update_amplitude(+AMPLITUDE_STEP)
                    elif seq == '[B':                      # DOWN arrow
                        _update_amplitude(-AMPLITUDE_STEP)
                elif key in ('q', 'Q', '\x03'):            # q, Q, or Ctrl+C
                    sys.stdout.write("\r\nQuitting...\r\n")
                    sys.stdout.flush()
                    break
                sys.stdout.write("\r")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        quit_requested.set()


def keyboard_listener():
    """Listen for UP/DOWN arrow keys to adjust amplitude (no link writes)."""
    print("Amplitude control: UP arrow (+5) | DOWN arrow (-5) | Q to quit")
    print(f"Amplitude: {amplitude}")
    if _IS_WINDOWS:
        _keyboard_listener_windows()
    else:
        _keyboard_listener_unix()


def run_test():
    # Initialize the EtactileKit object and connect over the chosen link
    etactilekit = ETactileKit()
    if not etactilekit.connect(MODE, serial_port=SERIAL_PORT, host=WIFI_HOST, device_id=TARGET_DEVICE_ID):
        print("Could not connect to the eTactileKit. Exiting.")
        return

    # Set up the kit and verify it: the settings go out in an order that can never overrun the scan
    # period, the sync check must report ELECTRODE_NUMBER, and the HV513 count is read. The electrode
    # mapping (application electrode -> hardware channel) defaults to electrode i -> channel i.
    if not etactilekit.configure(ELECTRODE_NUMBER, STIMULATION_MODE, PULSE_WIDTH, FREQUENCY,
                                 discharge_time=50, sense_pulse_height=0, sense_pulse_width=0):
        print("Setup failed. Exiting.")
        etactilekit.disconnect_etactilekit()
        return
    print("HV513 count:", etactilekit.hv513_num)
    print("ETactileKit setup complete.")

    # Start keyboard listener thread (link writes stay on the main thread)
    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()


    on_pattern  = [amplitude]*ELECTRODE_NUMBER
    off_pattern = [0]*ELECTRODE_NUMBER
    time.sleep(1)

    # Send the on and off pattern alternatively every X second
    delay_interval = 0.5
    # voltage_read_interval = 0.4
    last_pattern_sent_time = time.time()
    # last_voltage_read_time = last_pattern_sent_time

    last_sent_amplitude = amplitude
    flag = 0
    try:
        stream_patterns(etactilekit, on_pattern, off_pattern, last_sent_amplitude, flag, delay_interval,
                        last_pattern_sent_time)
    finally:
        # Zero pattern and sense height 0, then close (also on Ctrl+C)
        etactilekit.disconnect_etactilekit()


def stream_patterns(etactilekit, on_pattern, off_pattern, last_sent_amplitude, flag, delay_interval,
                    last_pattern_sent_time):
    while not quit_requested.is_set():
        current_time = time.time()
        if current_time - last_pattern_sent_time >= delay_interval: # send pattern every delay_interval seconds

            if amplitude != last_sent_amplitude:
                on_pattern = [amplitude]*ELECTRODE_NUMBER
                last_sent_amplitude = amplitude

            if not etactilekit.send_stim_pattern(on_pattern if flag else off_pattern):
                print("The link to the kit failed (the kit has zeroed every amplitude). Exiting.")
                return
            flag = 1 - flag
            last_pattern_sent_time = current_time
        time.sleep(0.001)

        # if current_time - last_voltage_read_time >= voltage_read_interval:
        #     voltages = etactilekit.get_voltage_readings(timeout=0.05)  # Read voltage data every voltage_read_interval seconds
        #     if voltages is not None:
        #         print(voltages[-8:])  # Print last 8 voltage readings
        #     last_voltage_read_time = current_time

if __name__ == "__main__":
    run_test()
