#include "adc_dac.h"

void initADC_DAC() {
    pinMode(DA_CS, OUTPUT);
    pinMode(AD_CS, OUTPUT);

    DAAD(0);
    delay(500);   //wait for 0.5 sec to achieve "stable" power on (especially for 300V)
  
    SPI.begin(SCLK, MISO, MOSI);
    SPI.setFrequency(32000000);
    SPI.setDataMode(SPI_MODE0);   //This may be the cause of instable stimulation?
}

short DAAD(int DA) {
    short AD;
    digitalWrite(DA_CS, LOW);      //enable clock
    digitalWrite(AD_CS, LOW);      //enable clock
    AD = SPI.transfer16(DA<<2);    //last two bits are don't care (2 control bits+12bit data+2 don't care bits)
    digitalWrite(DA_CS, HIGH);     //disable clock and load data
    digitalWrite(AD_CS, HIGH); 
    return AD >> 2;                //bottom 2bits are unnecessary(This is according to the AD7276 datasheet)
}