#include "adc_dac.h"
#include "soc/spi_struct.h"

void initADC_DAC() {
    pinMode(DA_CS, OUTPUT);
    pinMode(AD_CS, OUTPUT);
    gpio_fast_on(DA_CS);
    gpio_fast_on(AD_CS);

    SPI.begin(SCLK, MISO, MOSI);
    SPI.setFrequency(32000000);
    SPI.setDataMode(SPI_MODE0);

    DAAD(0);
}

// uint16_t IRAM_ATTR DAAD(uint16_t DA) {
    //     uint16_t AD;
    //     gpio_fast_off(DA_CS);        //enable clock
    //     gpio_fast_off(AD_CS);        //enable clock
    //     AD = SPI.transfer16(DA<<2);  //last two bits are don't care (2 control bits+12bit data+2 don't care bits)
    //     gpio_fast_on(DA_CS);         //disable clock and load data
    //     gpio_fast_on(AD_CS);         //disable clock and load data
    //     return AD >> 2;              //bottom 2bits are unnecessary(This is according to the AD7276 datasheet)
// }

uint16_t IRAM_ATTR DAAD(uint16_t DA) {
    uint16_t tx = DA << 2;
  
    // ESP32 SPI register buffer expects byte-swapped data for MSB-first 16-bit transfer.
    tx = (tx >> 8) | (tx << 8);
    
    GPIO.out1_w1tc.val = (1U << (DA_CS - 32)) | (1U << (AD_CS - 32));
  
    GPSPI2.ms_dlen.ms_data_bitlen = 15;
    
    GPSPI2.data_buf[0] = tx;
    GPSPI2.cmd.update = 1;
    while (GPSPI2.cmd.update);
  
    GPSPI2.cmd.usr = 1;
    while (GPSPI2.cmd.usr);
  
    GPIO.out1_w1ts.val = (1U << (DA_CS - 32)) | (1U << (AD_CS - 32));
  
    uint16_t rx = GPSPI2.data_buf[0] & 0xFFFF;
    rx = (rx >> 8) | (rx << 8);
  
    return rx >> 2;
}
