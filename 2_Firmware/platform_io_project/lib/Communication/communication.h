#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>
#include "configuration.h"

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
/*Communication links                                                      */
/*Serial (USB) and WiFi are both available. The first host to connect owns */
/*the board and the other link is refused until that host disconnects.     */
/************************************************************************* */
typedef enum : uint8_t {
    LINK_NONE   = 0,  // No host connected - listening on both links
    LINK_SERIAL = 1,  // A host has the USB serial port open
    LINK_WIFI   = 2   // A TCP client is connected
} Link;

extern volatile Link activeLink;  // Link that currently owns the board
extern uint32_t linkGeneration;   // Incremented whenever a host connects or disconnects

/************************************************************************* */
/*Begin Communication                                                      */
/************************************************************************* */
void initCommunication();

/************************************************************************* */
/*Track host connects/disconnects and receive serial data - call once per  */
/*parser iteration. Returns true while serial data is arriving, so the     */
/*parser polls again at once instead of sleeping.                          */
/************************************************************************* */
bool serviceCommunication();

/************************************************************************* */
/*Record whether the serial host is still polling the port. Call it during */
/*waits longer than a tick, so a port closed meanwhile is timed from when  */
/*the host stopped, not from when the wait ended.                          */
/************************************************************************* */
void sampleHostPresence();

/************************************************************************* */
/*Sleep until the serial host sends data or one tick passes. Call it from  */
/*the task that ran initCommunication(), when it has nothing to do.        */
/*Returns true if serial data woke it (possibly without sleeping at all).  */
/************************************************************************* */
bool waitForHostData();

/************************************************************************* */
/*Check if data is available                                               */
/************************************************************************* */
int isDataAvailable();

/************************************************************************* */
/*Write Byte values                                                        */
/************************************************************************* */
///Write 8-bit value
void writeInt_8(byte val);

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

#endif //COMMUNICATION_H