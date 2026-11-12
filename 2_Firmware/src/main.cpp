#include <Arduino.h>
#include "etactilekit.h"

void setup() {
  initEtactileKit();
}

void loop() {
  /*Host communication runs in its own task on core 0; stimulation runs in a timer interrupt on core 1*/
  /***********************************************/
  /*Add your code here*/
  /*loop() runs on core 1 between stimulation scans. The USB serial port carries the eTactileKit protocol, so do not use Serial, printf or std::cout (stdout is mirrored onto it)*/
  /***********************************************/
  delay(1);
}
