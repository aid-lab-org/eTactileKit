#include "switching.h"

int HV513Num; // Number of HV513 modules used(minimum should be 1 because the onboard HV513) - determined by stackSense()

void initSwitching() {
    pinMode(HV513_DIN, OUTPUT);
    pinMode(HV513_BL, OUTPUT);
    pinMode(HV513_POL, OUTPUT);
    pinMode(HV513_CLK, OUTPUT);
    pinMode(HV513_LE, OUTPUT);
    #if defined(ETACTILEKIT_BOARD)||defined(ETACTILEKIT_COMPACT_BOARD)
      pinMode(STACK_SENSE, INPUT);
    #endif
    stackSense(); // Detect the number of stacked switching boards and initialize the HV513 outputs
}

void hv513FastScan(int usWhichPin) {
    int ii, pin;
    static int pos;
    //Load S/R
    gpio_fast_off(HV513_LE); // Set LE low
    if (usWhichPin == 0) {
      gpio_fast_on(HV513_DIN);  // Set DIN high (setting the first bit)
      gpio_fast_on(HV513_CLK);  // Set CLK high
      gpio_fast_off(HV513_CLK); // Set CLK low
      pos = 0;
    } else {
      gpio_fast_off(HV513_DIN); // Set DIN low (clearing the first bit)
      pin = usWhichPin - pos;
      for (ii = 0; ii < pin; ii++) {
        gpio_fast_on(HV513_CLK);  // Set CLK high
        gpio_fast_off(HV513_CLK); // Set CLK low
      }
      pos = usWhichPin;
    }
    gpio_fast_on(HV513_LE); // Set LE high to latch the data
}

void hv513Clear(int hv513_num) {
    hv513FastScan(HV513_PIN_NUM * hv513_num);
}

void hv513Init(int hv513_num) { 
    int pin;
    int hv513_total = HV513_PIN_NUM * hv513_num;
    gpio_fast_on(HV513_POL);  // Set POL high
    gpio_fast_off(HV513_LE);  // Set LE low
    gpio_fast_off(HV513_CLK); // Set CLK low
    gpio_fast_on(HV513_BL);   // Set BL high

    gpio_fast_off(HV513_DIN); // Set DIN low (we are turning off all the outputs)
    for (pin = 0; pin < hv513_total; pin++) {
      gpio_fast_on(HV513_CLK);  // Set CLK high
      gpio_fast_off(HV513_CLK); // Set CLK low
    }
}

short stackSense() {
#if defined(ETACTILEKIT_BOARD)
  int stack_reading = 0;
  int stack_count;
  for (int i = 0; i < 50; i++) {
    stack_reading = stack_reading + analogRead(STACK_SENSE);
  }
  stack_reading = stack_reading / 50; //This is the average of 50 readings

  stack_count = round((9368.8636/stack_reading) - 1.51); //This is the formula to detect the number of boards. It is based on the voltage divider circuit.

  // Check the value of stack_reading against ranges
  if (stack_count == 1) {
    HV513Num = 1;
  } 
  else if (stack_count >= 2) {
    HV513Num = (stack_count - 1) * 8; // Each board has 8 HV513 outputs
  }
  else {
    HV513Num = 1; // Default value for out-of-range cases
  }
  hv513Init(HV513Num); //turnoff all the HV513-outputs when the number of boards is detected
  return HV513Num;
#elif defined(ETACTILEKIT_COMPACT_BOARD)
  int stack_reading = 0;
  int stack_count;
  for (int i = 0; i < 50; i++) {
    stack_reading = stack_reading + analogRead(STACK_SENSE);
  }
  stack_reading = stack_reading / 50; //This is the average of 50 readings

  stack_count = round((9368.8636/stack_reading) - 1.51); //This is the formula to detect the number of boards. It is based on the voltage divider circuit.

  // Check the value of stack_reading against ranges
  if (stack_count >= 1) {
    HV513Num = (stack_count-1) * 4; // Each board has 4 HV513 outputs
  } 
  else {
    HV513Num = 0; // Default value for out-of-range cases
  }
  hv513Init(HV513Num); //turnoff all the HV513-outputs when the number of boards is detected
  return HV513Num;
#elif defined(KAJI_LAB_BOARD)
  HV513Num = 8;
  hv513Init(HV513Num); //turnoff all the HV513-outputs when the number of boards is detected
  return HV513Num;
#else
  HV513Num = 0; // Default value for out-of-range cases
  hv513Init(HV513Num); //turnoff all the HV513-outputs when the number of boards is detected
  return HV513Num;
#endif
}
