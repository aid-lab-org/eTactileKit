#ifndef ETACTILEKIT_H
#define ETACTILEKIT_H

#include <Arduino.h>
#include "configuration.h"
#include "switching.h"
#include "adc_dac.h"
#include "communication.h"

extern unsigned char stim_pattern[MAX_ELECTRODE_NUM];
extern unsigned int voltage[MAX_ELECTRODE_NUM];

// extern TaskHandle_t th[1]; //Task handle for stimulation task - https://www.circuitstate.com/tutorials/how-to-write-parallel-multitasking-applications-for-esp32-using-freertos-arduino/

extern hw_timer_t *Timer0_Cfg; // Handle for the delays
extern hw_timer_t *Timer1_Cfg; // Handle for the stimulation timer

extern int   Polarity;                // 1:anodic, 0:cathodic
extern int   PulseHeight;             // Pulse height of the stimulation
extern int   PulseWidth;              // Pulse width of the stimulation
extern int   SensePulseHeight;        // Pulse height to measure the impedance
extern int   SensePulseWidth;         // Pulse width to measure the impedance
extern int   ChannelDischargeTime;    // Discharge time for the channel
extern float StimulationTimePeriod; // Time period for the stimulation in ms - 1/frequency set to 60Hz by default

extern int ElectrodeNum;            // Number of currently active electrodes

/**********************************************************************/
/*  delay_exact_us - delays the execution for a specified number of   */
/*  microseconds. This function is used to ensure precise timing      */
/**********************************************************************/
void IRAM_ATTR delay_exact_us(int us);

/**********************************************************************/
/*  setPeriodUs - sets the period of the timer in microseconds. This  */
/*  function is used to set the timer period for the stimulation task.*/
/**********************************************************************/
void setPeriodUs(uint32_t us);

/**********************************************************************/
/*  Timer1_Stimulate_ISR - interrupt service routine for the timer    */
/*  This function is called when the timer interrupt occurs and       */
/*  handles the stimulation of the electrodes.                        */
/**********************************************************************/
void IRAM_ATTR Timer1_Stimulate_ISR();

/**********************************************************************/
/*  initEtactileKit - initializes the eTactileKit board and starts the*/
/*  stimulation task.                                                 */
/**********************************************************************/
void initEtactileKit();

/**********************************************************************/
/*  stimulate - multi-core loop running the stimualte task            */
/**********************************************************************/
// void stimulate(void *pvParameters);

int monoPhasicPulse(int stim_pulse_height, int stim_pulse_width);

int biPhasicPulse(int height_a, int width_a, int height_b, int width_b);

void dischargeChannel(int discharge_time);

/**********************************************************************/
/*  runEtactileKit - main loop for the eTactileKit board              */
/*  This function should be called in the main loop of the program.   */
/*  It handles the communication with the eTactileKit board and       */
/*  processes the commands received from the PC.                      */
/**********************************************************************/
void runEtactileKit();

#endif //ETACTILEKIT_H