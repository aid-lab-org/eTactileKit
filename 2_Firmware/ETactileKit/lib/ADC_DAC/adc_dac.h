#ifndef ADC_DAC_H
#define ADC_DAC_H

#include <Arduino.h>
#include <SPI.h>
#include "definitions.h"

/******************************************************************************/
/*  Initialize the ADC and DAC                                                */
/******************************************************************************/
void initADC_DAC();

/******************************************************************************/
/* DA output by AD5452 and AD input by AD7276(SPI)                            */
/******************************************************************************/
short DAAD(int DA);

#endif //ADC_DAC_H