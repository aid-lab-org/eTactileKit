#ifndef SWITCHING_H
#define SWITCHING_H

#include <Arduino.h>
#include "configuration.h"

#define HV513_PIN_NUM 8 //Number of pins in a HV513 module
#define HV513_MAX_NUM 255 //Largest chip count the one-byte reply to the host can carry

extern int HV513Num; // Number of HV513 chips detected by stackSense() and reported to the host

/******************************************************************************/
/*  Initialize the switching board                                            */
/******************************************************************************/
void initSwitching();

/******************************************************************************/
/*  hv513FastScan                                                             */
/*  MAKE SURE THAT YOU INITIALIZE THIS FUNCTION BY FIRST CALLING              */
/*  hv513FastScan(0);                                                         */
/*  See manual for detail of this function.                                   */
/******************************************************************************/
void IRAM_ATTR hv513FastScan(int usWhichPin);

/******************************************************************************/
/*  HV513 Clear                                                               */
/*  Deselects every output of the chain                                       */
/******************************************************************************/
void IRAM_ATTR hv513Clear();

/******************************************************************************/
/* HV513 init                                                                 */
/* Turn off all the HV513-outputs                                             */
/******************************************************************************/
void hv513Init();

/**********************************************************************/
/*  stackSense - detects the number of stacked swtiching boards       */
/**********************************************************************/
short stackSense();

#endif //SWITCHING_H