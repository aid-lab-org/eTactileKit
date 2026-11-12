#ifndef ETACTILEKIT_H
#define ETACTILEKIT_H

#include <Arduino.h>
#include "configuration.h"
#include "switching.h"
#include "adc_dac.h"
#include "communication.h"

extern hw_timer_t *Timer0_Cfg; // Busy-wait timer for the pulse timing
extern hw_timer_t *Timer1_Cfg; // Stimulation timer; each alarm runs one scan

typedef enum {
    MONOPHASIC_STIMULATION = 0,
    BIPHASIC_STIMULATION = 1,
    IMPEDANCE_ONLY = 2
} Mode;

/*Stimulation parameters set by host commands (command task, core 0); the interrupt takes   */
/*them at the start of each scan. Polarity is applied by the interrupt, and scans use the    */
/*electrode count of the published pattern. Read them only.                                  */
extern volatile Mode   StimulationMode;        // Mode of the stimulation
extern volatile int   PulseWidth;              // Pulse width of the stimulation
extern volatile int   SensePulseHeight;        // Pulse height to measure the impedance
extern volatile int   SensePulseWidth;         // Pulse width to measure the impedance
extern volatile int   ChannelDischargeTime;    // Discharge time for the channel
extern volatile int   ElectrodeNum;            // Number of electrodes set by the host; scans use it once its pattern is published
extern volatile int   Polarity;                // Polarity of the scan in progress (1:anodic, 0:cathodic), applied by the interrupt

/**********************************************************************/
/*  delay_exact_us - delays the execution for a specified number of   */
/*  microseconds. This function is used to ensure precise timing      */
/**********************************************************************/
void IRAM_ATTR delay_exact_us(int us);

/**********************************************************************/
/*  setPeriodUs - sets the stimulation period in microseconds. The    */
/*  interrupt programs it between scans.                              */
/**********************************************************************/
void setPeriodUs(uint32_t us);

/**********************************************************************/
/*  Timer1_Stimulate_ISR - interrupt service routine for the timer    */
/*  This function is called when the timer interrupt occurs and       */
/*  handles the stimulation of the electrodes.                        */
/**********************************************************************/
void IRAM_ATTR Timer1_Stimulate_ISR();

/**********************************************************************/
/*  initEtactileKit - initializes the eTactileKit board, starts the   */
/*  stimulation timer interrupt on the calling core (call it from     */
/*  setup(), which runs on core 1) and the command task on core 0.    */
/**********************************************************************/
void initEtactileKit();

uint16_t IRAM_ATTR monoPhasicPulse(int stim_pulse_height, int stim_pulse_width);

uint16_t IRAM_ATTR biPhasicPulse(int height_a, int width_a, int height_b, int width_b);

void IRAM_ATTR dischargeChannel(int discharge_time);

#endif //ETACTILEKIT_H
