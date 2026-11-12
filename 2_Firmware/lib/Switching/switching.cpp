#include "switching.h"

int HV513Num; // Number of HV513 chips detected by stackSense() and reported to the host

// Shifts that take a bit past the end of the chain: the outputs of the detected chips, and at least
// MAX_ELECTRODE_NUM, which covers every output the electrode number can address when the detection
// reads too low. Written by stackSense(), which runs while no scan can.
static int chainOutputs = MAX_ELECTRODE_NUM;

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

void IRAM_ATTR hv513FastScan(int usWhichPin) {
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

// The scan selects one output by shifting a single '1' along the chain. Shifting it to
// chainOutputs moves it past the end of the chain, so every output is deselected.
void IRAM_ATTR hv513Clear() {
    hv513FastScan(chainOutputs);
}

void hv513Init() {
    int pin;
    gpio_fast_on(HV513_POL);  // Set POL high
    gpio_fast_off(HV513_BL);  // Set BL low: with POL high, every output is off while the register is cleared
    gpio_fast_off(HV513_LE);  // Set LE low
    gpio_fast_off(HV513_CLK); // Set CLK low

    gpio_fast_off(HV513_DIN); // Set DIN low (we are turning off all the outputs)
    for (pin = 0; pin < chainOutputs; pin++) {
      gpio_fast_on(HV513_CLK);  // Set CLK high
      gpio_fast_off(HV513_CLK); // Set CLK low
    }
    gpio_fast_on(HV513_LE);   // Set LE high to latch the cleared register
    gpio_fast_on(HV513_BL);   // Set BL high
}

#if defined(ETACTILEKIT_BOARD) || defined(ETACTILEKIT_COMPACT_BOARD)
// Number of boards in the stack, from the voltage divider on STACK_SENSE; 0 if the reading is not usable.
static int stackCount() {
  int stack_reading = 0;
  for (int i = 0; i < 50; i++) {
    stack_reading = stack_reading + analogRead(STACK_SENSE);
  }
  stack_reading = stack_reading / 50; //This is the average of 50 readings
  if (stack_reading <= 0) {
    return 0;
  }
  return lround((9368.8636/stack_reading) - 1.51); //This is the formula to detect the number of boards. It is based on the voltage divider circuit.
}
#endif

short stackSense() {
#if defined(ETACTILEKIT_BOARD)
  const int stack_count = stackCount();
  int chips = 1; // The onboard HV513; also the default for out-of-range cases
  if (stack_count >= 2 && (stack_count - 1) * 8 <= HV513_MAX_NUM) {
    chips = (stack_count - 1) * 8; // Each board has 8 HV513 chips
  }
  HV513Num = chips;
#elif defined(ETACTILEKIT_COMPACT_BOARD)
  const int stack_count = stackCount();
  int chips = 0; // Default value for out-of-range cases
  if (stack_count >= 1 && (stack_count - 1) * 4 <= HV513_MAX_NUM) {
    chips = (stack_count - 1) * 4; // Each board has 4 HV513 chips
  }
  HV513Num = chips;
#else
  HV513Num = 0;
#endif
  chainOutputs = max(MAX_ELECTRODE_NUM, HV513Num * HV513_PIN_NUM);
  hv513Init(); //turnoff all the HV513-outputs when the number of boards is detected
  return HV513Num;
}
