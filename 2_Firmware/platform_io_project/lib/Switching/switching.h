#ifndef SWITCHING_H
#define SWITCHING_H

#include <Arduino.h>
#include "configuration.h"

#define HV513_PIN_NUM 8 //Number of pins in a HV513 module

extern int HV513Num; // Number of HV513 modules used(minimum should be 1 because the onboard HV513) - determined by stackSense()

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
void hv513FastScan(int usWhichPin);

/******************************************************************************/
/*  HV513 Clear                                                               */
/******************************************************************************/
void hv513Clear(int hv513_num);

/******************************************************************************/
/* HV513 init                                                                 */
/* Turn off all the HV513-outputs                                             */
/******************************************************************************/
void hv513Init(int hv513_num);

/**********************************************************************/
/*  stackSense - detects the number of stacked swtiching boards       */
/**********************************************************************/
short stackSense();

#endif //SWITCHING_H