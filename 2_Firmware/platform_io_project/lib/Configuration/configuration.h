#ifndef CONFIGURATION_H
#define CONFIGURATION_H

#include <Arduino.h>

/************************************************************************* */
/*Board definitions - Uncomment for correct board configuration            */
/************************************************************************* */
// #define ETACTILEKIT_BOARD
#define ETACTILEKIT_COMPACT_BOARD
// #define KAJI_LAB_BOARD

/************************************************************************* */
/*Communication Type Used - Uncomment correct type                         */
/************************************************************************* */
#define SERIAL_COMMUNICATION
// #define BLE_COMMUNICATION
// #define WIFI_COMMUNICATION


/************************************************************************* */
/*Pin Assignment for the board used                                        */
/************************************************************************* */
#define SCLK                                     7 //GPIO7
#define MISO                                     8 //GPIO8
#define MOSI                                     9 //GPIO9
#define DA_CS                                   44 //GPIO44
#define AD_CS                                   43 //GPIO43
#define HV513_BL                                 1 //GPIO1
#define HV513_LE                                 2 //GPIO2
#define HV513_POL                                3 //GPIO3
#define HV513_CLK                                4 //GPIO4
#define HV513_DIN                                5 //GPIO5

#if defined(ETACTILEKIT_BOARD)|| defined(ETACTILEKIT_COMPACT_BOARD)
#define STACK_SENSE                              6 //GPIO6
#endif

/************************************************************************* */
/*Global variables                                                         */
/************************************************************************* */
#if defined(SERIAL_COMMUNICATION)
#define BAUD_RATE 921600       //Baud rate for serial communication
#endif

#define MAX_ELECTRODE_NUM 256  //Maximum Number of electrodes supported by the board

static inline void gpio_fast_on (int pin)  {
    if (pin < 32) { GPIO.out_w1ts = 1U << pin; }       // 0-31
    else          { GPIO.out1_w1ts.val = 1U << (pin-32); }
}

static inline void gpio_fast_off(int pin)  {
    if (pin < 32) { GPIO.out_w1tc = 1U << pin; }
    else          { GPIO.out1_w1tc.val = 1U << (pin-32); }
}

#endif //CONFIGURATION_H