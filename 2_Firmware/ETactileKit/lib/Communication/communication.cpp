#include "communication.h"
void initCommunication(int baudRate) {
  Serial.begin(baudRate);
}

void writeByte(uint8_t byte) {
  Serial.write(byte);
}

unsigned char readByte() {
  return Serial.read();
}

int isDataAvailable() {
  return Serial.available();
}