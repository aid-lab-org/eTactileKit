#ifndef ETACTILEKIT_H
#define ETACTILEKIT_H

#include <Arduino.h>
#include "configuration.h"
#include "switching.h"
#include "adc_dac.h"
#include "communication.h"

extern volatile uint16_t stim_pattern[MAX_ELECTRODE_NUM];
extern volatile byte voltage[MAX_ELECTRODE_NUM * 2];

// extern TaskHandle_t th[1]; //Task handle for stimulation task - https://www.circuitstate.com/tutorials/how-to-write-parallel-multitasking-applications-for-esp32-using-freertos-arduino/

extern hw_timer_t *Timer0_Cfg; // Handle for the delays
extern hw_timer_t *Timer1_Cfg; // Handle for the stimulation timer
extern hw_timer_t *Timer2_Cfg; // Handle for the hardware timer for communication

typedef enum {
    MONOPHASIC_STIMULATION = 0,
    BIPHASIC_STIMULATION = 1,
    IMPEDANCE_ONLY = 2
} Mode;

extern volatile int   Polarity;                // 1:anodic, 0:cathodic
extern volatile Mode   StimulationMode;        // Mode of the stimulation 
extern volatile int   PulseWidth;              // Pulse width of the stimulation 
extern volatile int   SensePulseHeight;        // Pulse height to measure the impedance 
extern volatile int   SensePulseWidth;         // Pulse width to measure the impedance 
extern volatile int   ChannelDischargeTime;    // Discharge time for the channel 
extern volatile float StimulationTimePeriod;   // Time period for the stimulation in ms - 1/frequency set to 60Hz by default 

extern volatile int ElectrodeNum;              // Number of currently  active electrodes

extern volatile bool SendingVoltages;          // Flag to indicate if a command is being processed

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

uint16_t IRAM_ATTR monoPhasicPulse(int stim_pulse_height, int stim_pulse_width);

uint16_t IRAM_ATTR biPhasicPulse(int height_a, int width_a, int height_b, int width_b);

void IRAM_ATTR dischargeChannel(int discharge_time);

/**********************************************************************/
/*  runEtactileKit - main loop for the eTactileKit board              */
/*  This function should be called in the main loop of the program.   */
/*  It handles the communication with the eTactileKit board and       */
/*  processes the commands received from the PC.                      */
/**********************************************************************/
void runEtactileKit();

#endif //ETACTILEKIT_H
