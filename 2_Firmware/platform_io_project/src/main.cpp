#include <Arduino.h>
#include "etactilekit.h"

void setup() {
  initEtactileKit();
}

void loop() {
  /*BLE and WiFi Run in Core 0 and the loop runs in Core 1*/
  runEtactileKit();
  /***********************************************/
  /*Add your code here*/ 
  /*Make sure the loop is not stalled to make sure that eTactileKit communication is not interfered severely*/
  /***********************************************/
}