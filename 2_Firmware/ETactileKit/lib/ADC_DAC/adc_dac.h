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
/* THe SPI MOSI is connected to the DAC and MISO is from the ADC output       */
/* This eliminates the requirement for having seperate communication channels */
/******************************************************************************/
int DAAD(int DA);

#endif //ADC_DAC_H