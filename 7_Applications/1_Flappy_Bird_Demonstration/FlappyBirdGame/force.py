import serial
import time

PC_ESP32_GET_FSR_READING = 0xFF


class ForceSensor:
    def __init__(self, communication):
        self.comm = communication  # Communication object for serial communication tasks

    def get_force_reading(self):
        self.comm.write_serial_bytes(PC_ESP32_GET_FSR_READING)
        time.sleep(0.005)
        rcv = self.comm.read_serial_string()
        return int(rcv)