#include "adc_dac.h"

void initADC_DAC() {
    pinMode(DA_CS, OUTPUT);
    pinMode(AD_CS, OUTPUT);

    SPI.begin(SCLK, MISO, MOSI);
    SPI.setFrequency(32000000);
    SPI.setDataMode(SPI_MODE0);
    
    DAAD(0);
}

int DAAD(int DA) {
    int AD;
    gpio_fast_off(DA_CS);        //enable clock
    gpio_fast_off(AD_CS);        //enable clock
    AD = SPI.transfer16(DA<<2);  //last two bits are don't care (2 control bits+12bit data+2 don't care bits)
    gpio_fast_on(DA_CS);         //disable clock and load data
    gpio_fast_on(AD_CS);         //disable clock and load data
    return AD >> 2;              //bottom 2bits are unnecessary(This is according to the AD7276 datasheet)
}