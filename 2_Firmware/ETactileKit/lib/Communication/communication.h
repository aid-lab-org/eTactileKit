#ifndef COMMUNICATiON_H
#define COMMUNICATiON_H

#include <Arduino.h>

/************************************************************************* */
/*Commands for communication and accessing controller                      */
/************************************************************************* */   
#define PC_ESP32_MEASURE_REQUEST                 0xFF //Request to measure the impedance of all electrodes   
#define PC_ESP32_STIM_PATTERN                    0xFE //Stimulation pattern for all electrodes
#define PC_ESP32_STIMULATION_POLARITY            0xFD //Polarity of the stimulation - ANODIC or CATHODIC
#define PC_ESP32_ELECTRODE_NUM                   0xFC //Number of electrodes used for the stimulation
#define PC_ESP32_STIMULATION_PULSE_HEIGHT        0xFB //Pulse height of the stimulation
#define PC_ESP32_STIMULATION_PULSE_WIDTH         0xFA //Pulse width of the stimulation
#define PC_ESP32_SENSE_PULSE_HEIGHT              0xF9 //Pulse height for impedance measurement
#define PC_ESP32_SENSE_PULSE_WIDTH               0xF8 //Pulse width for impedance measurement
#define PC_ESP32_CHANNEL_DISCHARGE_TIME          0xF7 //Discharge time for the channel
#define PC_ESP32_STIMULATION_FREQUENCY           0xF6 //Frequency of the stimulation
#define PC_ESP32_HV513_NUM_REQUEST               0xF5 //Request to get the number of HV513 modules used
/************************************************************************* */

/************************************************************************* */
/*Begin Communication                                                      */
/************************************************************************* */
void initCommunication(int baudRate);

/************************************************************************* */
/*Check if data is available                                               */
/************************************************************************* */
int  isDataAvailable();

/************************************************************************* */
/*Write Byte values                                                        */
/************************************************************************* */
///Write 8-bit value
void writeInt_8(byte val);

///Write 16-bit value with low byte first
void writeInt_16(uint16_t val);

/************************************************************************* */
/*Read Byte values                                                         */
/************************************************************************* */
///Read 8-bit value
byte readInt_8();

///Read 16-bit value with low byte first
uint16_t readInt_16();
/************************************************************************* */

#endif //COMMUNICATION_H