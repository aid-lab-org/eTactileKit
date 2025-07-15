#ifndef DEFINITIONS_H
#define DEFINITIONS_H

#include <Arduino.h>

/************************************************************************* */
/*Board definitions                                                        */
/************************************************************************* */
#define ETACTILEKIT_BOARD
// #define COMPACT_BOARD

/************************************************************************* */
/*Pin Assignment for the board used                                        */
/************************************************************************* */
#if defined (ETACTILEKIT_BOARD)
  #define SCLK                                     7 //GPIO7
  #define MISO                                     8 //GPIO8
  #define MOSI                                     9 //TPIO9
  #define DA_CS                                   44 //GPIO44
  #define AD_CS                                   43 //GPIO43
  #define HV513_BL                                 1 //GPIO1
  #define HV513_LE                                 2 //GPIO2
  #define HV513_POL                                3 //GPIO3
  #define HV513_CLK                                4 //GPIO4
  #define HV513_DIN                                5 //GPIO5
  #define STACK_SENSE                              6 //GPIO6
#elif defined (COMPACT_BOARD)
  #define SCLK                                     7 //GPIO7
  #define MISO                                     8 //GPIO8
  #define MOSI                                     9 //TPIO9
  #define DA_CS                                   44 //GPIO44
  #define AD_CS                                   43 //GPIO43
  #define HV513_BL                                 1 //GPIO1
  #define HV513_LE                                 2 //GPIO2
  #define HV513_POL                                3 //GPIO3
  #define HV513_CLK                                4 //GPIO4
  #define HV513_DIN                                5 //GPIO5
#else
  #error "Please define the board used"
#endif

/************************************************************************* */
/*Global variables                                                         */
/************************************************************************* */
#define BAUD_RATE 921600       //Baud rate for serial communication
#define MAX_ELECTRODE_NUM 256  //Maximum Number of electrodes supported by the board


#endif //DEFINITIONS_H