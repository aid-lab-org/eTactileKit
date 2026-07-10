#ifndef COMMUNICATiON_H
#define COMMUNICATiON_H

#include <Arduino.h>
#include "configuration.h"

extern bool deviceConnected;
/************************************************************************* */
/*Commands for communication and accessing controller                      */
/************************************************************************* */   
#define PC_ESP32_MEASURE_REQUEST                 0xFF //Request to measure the impedance of all electrodes   
#define PC_ESP32_STIM_PATTERN                    0xFE //Stimulation pattern for all electrodes
#define PC_ESP32_STIMULATION_POLARITY            0xFD //Polarity of the stimulation - ANODIC or CATHODIC
#define PC_ESP32_ELECTRODE_NUM                   0xFC //Number of electrodes used for the stimulation
#define PC_ESP32_STIM_MODE                       0xFB //Mode of the stimulation
#define PC_ESP32_STIMULATION_PULSE_WIDTH         0xFA //Pulse width of the stimulation
#define PC_ESP32_SENSE_PULSE_HEIGHT              0xF9 //Pulse height for impedance measurement
#define PC_ESP32_SENSE_PULSE_WIDTH               0xF8 //Pulse width for impedance measurement
#define PC_ESP32_CHANNEL_DISCHARGE_TIME          0xF7 //Discharge time for the channel
#define PC_ESP32_STIMULATION_FREQUENCY           0xF6 //Frequency of the stimulation
#define PC_ESP32_HV513_NUM_REQUEST               0xF5 //Request to get the number of HV513 modules used
#define PC_ESP32_SYNC_CHECK                      0xF4 // (setup verification)
/************************************************************************* */

/************************************************************************* */
/*Begin Communication                                                      */
/************************************************************************* */
void initCommunication();

/************************************************************************* */
/*Check if data is available                                               */
/************************************************************************* */
int isDataAvailable();

/************************************************************************* */
/*Write Byte values                                                        */
/************************************************************************* */
///Write 8-bit value
void writeInt_8(byte val);

///Write 16-bit value with low byte first
void writeInt_16(uint16_t val);

///Write a raw byte array — preferred for bulk data (e.g. voltage response)
void writeBytes(const byte* data, size_t len);

/************************************************************************* */
/*Read Byte values                                                         */
/************************************************************************* */
///Read 8-bit value
byte readInt_8();

///Read 16-bit value with low byte first
uint16_t readInt_16();
/************************************************************************* */

#if defined(WIFI_COMMUNICATION)
#include <WiFi.h>
#include <WiFiAP.h>
#include <ESPmDNS.h>
#include <AsyncUDP.h>

// WiFi server and client object declarations
extern WiFiServer server;
extern WiFiClient client;
extern bool wifiSTAMode;        // true = STA mode, false = AP fallback

// Unique per-board identity + discovery responder
extern char deviceId[7];        // 6 hex chars (from MAC) + NUL, e.g. "A1B2C3"
extern AsyncUDP discoveryUdp;   // Answers UDP discovery probes (event-driven, network core)

// Function Declarations
void checkClientConnection();

#endif

#if defined(BLE_COMMUNICATION)

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Server name
#define DEVICE_NAME "eTactileKit_BLE"

// UUIDs for the Nordic UART Service (Standard for Serial over BLE)
#define SERVICE_UUID           "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define CHARACTERISTIC_UUID_RX "6E400002-B5A3-F393-E0A9-E50E24DCCA9E" // Python writes to this
#define CHARACTERISTIC_UUID_TX "6E400003-B5A3-F393-E0A9-E50E24DCCA9E" // ESP32 notifies this

// --- Circular Buffer Implementation for Robustness ---
#define RX_BUFFER_SIZE 1024 // Size of the software buffer — must exceed the largest payload (MAX_ELECTRODE_NUM * 2 = 512 B) since the parser waits for a complete payload before reading

class RxBuffer {
  public:
    volatile uint8_t buffer[RX_BUFFER_SIZE];
    volatile int head = 0;
    volatile int tail = 0;

    void write(uint8_t data) {
      int next = (head + 1) % RX_BUFFER_SIZE;
      if (next != tail) { // Don't overflow
        buffer[head] = data;
        head = next;
      }
    }

    int read() {
      if (head == tail) return -1; // Empty
      int val = buffer[tail];
      tail = (tail + 1) % RX_BUFFER_SIZE;
      return val;
    }

    int available() {
      return (RX_BUFFER_SIZE + head - tail) % RX_BUFFER_SIZE;
    }
};
// ----------------------------------------------------

// Global variables
extern RxBuffer bleRxBuffer;
#endif

#endif //COMMUNICATION_H