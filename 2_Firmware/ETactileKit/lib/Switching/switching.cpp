#include "switching.h"

int HV513Num; // Number of HV513 modules used(minimum should be 1 because the onboard HV513) - determined by stackSense()

void initSwitching() {
    pinMode(HV513_DIN, OUTPUT);
    pinMode(HV513_BL, OUTPUT);
    pinMode(HV513_POL, OUTPUT);
    pinMode(HV513_CLK, OUTPUT);
    pinMode(HV513_LE, OUTPUT);
    #if defined(ETACTILEKIT_BOARD)
      pinMode(STACK_SENSE, INPUT);
    #endif
}

void hv513FastScan(int usWhichPin) {
    int ii, pin;
    static int pos;
    //Load S/R
    digitalWrite(HV513_LE, LOW);
    if (usWhichPin == 0) {
      digitalWrite(HV513_DIN, HIGH);
      digitalWrite(HV513_CLK, HIGH);
      digitalWrite(HV513_CLK, LOW);
      pos = 0;
    } else {
      digitalWrite(HV513_DIN, LOW);
      pin = usWhichPin - pos;
      for (ii = 0; ii < pin; ii++) {
        digitalWrite(HV513_CLK, HIGH);
        digitalWrite(HV513_CLK, LOW);
      }
      pos = usWhichPin;
    }
    digitalWrite(HV513_LE, HIGH); //added
}

void hv513Clear(int hv513_num) {
    hv513FastScan(HV513_PIN_NUM * hv513_num);
}

void hv513Init(int hv513_num) { 
    int pin;
    int hv513_total = HV513_PIN_NUM * hv513_num;
  
    digitalWrite(HV513_POL, HIGH);
    digitalWrite(HV513_LE, LOW);
    digitalWrite(HV513_CLK, LOW);
  
    digitalWrite(HV513_BL, HIGH);
    digitalWrite(HV513_DIN, LOW);
    for (pin = 0; pin < hv513_total; pin++) {
      digitalWrite(HV513_CLK, HIGH);
      digitalWrite(HV513_CLK, LOW);
    }
}

short stackSense() {
  #if defined(ETACTILEKIT_BOARD)
    int stack_reading = 0;
    int stack_count;
    for (int i = 0; i < 50; i++) {
      stack_reading = stack_reading + analogRead(STACK_SENSE);
    }
    stack_reading = stack_reading / 50; //This is the average of 10 readings

    stack_count = round((9368.8636/stack_reading) - 1.51); //This is the formula to detect the number of boards. It is based on the voltage divider circuit.

    // Check the value of stack_reading against ranges
    if (stack_count == 1) {
      HV513Num = 1;
    } 
    else if (stack_count == 2) {
      HV513Num = 8;
    } 
    else if (stack_count == 3) {
      HV513Num = 16;
    } 
    else if (stack_count == 4) {
      HV513Num = 24;
    } 
    else {
      HV513Num = 1; // Default value for out-of-range cases
    }
  #elif defined(COMPACT_BOARD)
    HV513Num = 8;
  #endif

  hv513Init(HV513Num); //turnoff all the HV513-outputs when the number of boards is detected
  return HV513Num;
}