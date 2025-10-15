#include "communication.h"
void initCommunication(int baudRate) {
  Serial.begin(baudRate);
}

void writeInt_8(byte val) {
  Serial.write(val);
}

void writeInt_16(uint16_t val) {
  byte arr[2] = { (byte)(val & 0xFF), (byte)((val >> 8) & 0xFF) };
  Serial.write(arr, 2);   // Send the array of bytes in the little-endian order
}

byte readInt_8() {
  return Serial.read();
}

uint16_t readInt_16() {
  byte arr[2];
  Serial.read(arr, 2); // Read two bytes into the array
  return (uint16_t)(arr[0] | (arr[1] << 8)); // Combine the two bytes into a single uint16_t
}

int isDataAvailable() {
  return Serial.available();
}