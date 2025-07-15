#ifndef ETACTILEKIT_H
#define ETACTILEKIT_H

#include <Arduino.h>
#include "definitions.h"
#include "switching.h"
#include "adc_dac.h"
#include "communication.h"

extern unsigned char stim_pattern[MAX_ELECTRODE_NUM];
extern unsigned char voltage[MAX_ELECTRODE_NUM];

extern TaskHandle_t th[1]; //Task handle for stimulation task - https://www.circuitstate.com/tutorials/how-to-write-parallel-multitasking-applications-for-esp32-using-freertos-arduino/

extern int   Polarity;                // 1:anodic, 0:cathodic
extern int   PulseHeight;             // Pulse height of the stimulation
extern int   PulseWidth;              // Pulse width of the stimulation
extern int   SensePulseHeight;        // Pulse height to measure the impedance
extern int   SensePulseWidth;         // Pulse width to measure the impedance
extern int   ChannelDischargeTime;    // Discharge time for the channel
extern float StimulationTimePeriod; // Time period for the stimulation in ms - 1/frequency set to 60Hz by default

extern int ElectrodeNum;            // Number of currently active electrodes

void initEtactileKit();

void stimulate(void *pvParameters);

void runEtactileKit();

#endif //ETACTILEKIT_H