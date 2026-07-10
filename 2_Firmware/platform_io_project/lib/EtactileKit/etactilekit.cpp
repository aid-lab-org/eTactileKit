#include "etactilekit.h"

volatile uint16_t stim_pattern[MAX_ELECTRODE_NUM] = {0};
volatile byte voltage[MAX_ELECTRODE_NUM * 2] = {0};

// TaskHandle_t th[1];

hw_timer_t *Timer0_Cfg = NULL;   // Handle for the hardware timer for setting delays
hw_timer_t *Timer1_Cfg = NULL;   // Handle for the hardware timer for the ADC
hw_timer_t *Timer2_Cfg = NULL;   // Handle for the hardware timer for communication

volatile int Polarity                 = 1;    
volatile Mode StimulationMode         = MONOPHASIC_STIMULATION;
volatile int PulseWidth               = 0;
volatile int SensePulseHeight         = 0;
volatile int SensePulseWidth          = 0;
volatile int ChannelDischargeTime     = 0;   
volatile float StimulationTimePeriod  = 10000.0; // Time period for the stimulation in us - 1/frequency set to 100Hz by default

volatile int ElectrodeNum             = 0;

volatile bool SendingVoltages = false;

void initEtactileKit() {
    initSwitching();
    initADC_DAC();
    initCommunication();

    // start the timer
    Timer0_Cfg = timerBegin(0, 40, true); //(timer id, prescaler, count up) - look https://deepbluembedded.com/esp32-timers-timer-interrupt-tutorial-arduino-ide/

    // xTaskCreatePinnedToCore(stimulate,"stimulate", 4096, NULL, 3, &th[0], 1); //Task for stimulation. Higher priority than main void loop()
    Timer1_Cfg = timerBegin(1, 40, true);
    timerAttachInterrupt(Timer1_Cfg, &Timer1_Stimulate_ISR, true);
    timerAlarmWrite(Timer1_Cfg, (int)StimulationTimePeriod*2, true);
    timerAlarmEnable(Timer1_Cfg);

    // Timer for communication timeouts. The prescaler field is 16-bit, so
    // values above 65535 silently truncate (80000 would become 14464).
    // 80MHz/80 = 1MHz, so each tick is 1us.
    Timer2_Cfg = timerBegin(2, 80, true);
}

void IRAM_ATTR delay_exact_us(int us) {
  if (us < 3) {
    us = 3; // minimum delay
  }
  us = (int)(us * 2.0 - 5.4); // 2.0*us - 5.5

  timerRestart(Timer0_Cfg);
  while (timerRead(Timer0_Cfg) < us);
}

void setPeriodUs(uint32_t us)
{
    timerAlarmDisable(Timer1_Cfg);
    timerAlarmWrite(Timer1_Cfg, us*2, true);  // *2 because the tick time is 0.5us--> 40/80MHz
    timerAlarmEnable(Timer1_Cfg);
}


uint16_t IRAM_ATTR monoPhasicPulse(int stim_pulse_height, int stim_pulse_width) {
  /*The DAAD pulse takes aroudn 6.6 to execute. The SPI values are written midway
  so the effective activation time is at around 3.3us*/
  uint16_t AD;
  if (stim_pulse_width < 7) {
    DAAD(stim_pulse_height);  // takes 6.6us
  }
  else {
    DAAD(stim_pulse_height);  // takes 6.6us
    delay_exact_us(stim_pulse_width - 7); // Delay for the pulse width
  }
  AD = DAAD(0); // takes 6.6us (The reading from the ADC is done before writing 0 to the DAC)
  return AD;    // Return the value read from the ADC
}


uint16_t IRAM_ATTR biPhasicPulse(int height_a, int width_a, int height_b, int width_b) {
  uint16_t AD;
  // First phase: same polarity as set by Polarity variable
  monoPhasicPulse(height_a, width_a); // Call the function to generate a mono-phasic pulse

  // Second phase: opposite polarity
  if (Polarity == 0){    //Cathodic Stimulation
    gpio_fast_on(HV513_POL);  // Set the polarity to anodic
  } else {                 //Anodic Stimulation
    gpio_fast_off(HV513_POL); // Set the polarity to cathodic
  }
  AD = monoPhasicPulse(height_b, width_b); // Call the function to generate a mono-phasic pulse
  return AD; // Return the value read from the ADC
}


void IRAM_ATTR dischargeChannel(int discharge_time) {
  // DAC is already 0 from the final DAAD(0) in monoPhasicPulse — no redundant SPI write here
  // POL = 1 and BL = 0 means all channels disabled (off)
  gpio_fast_on(HV513_POL);  // Set the polarity to ground
  gpio_fast_off(HV513_BL);  // Set the BL pin to low
  if (discharge_time > 7) {
    delay_exact_us(discharge_time - 7); // Delay for the pulse width
  }
  gpio_fast_on(HV513_BL);   // Reenable the HV513s
}


void IRAM_ATTR Timer1_Stimulate_ISR() { // Timer interrupt service routine
  timerAlarmDisable(Timer1_Cfg); // Disable the timer to prevent re-entrancy if the stimulation takes longer than the timer period

  int AD, ch, PulseHeight;
  const int n          = ElectrodeNum;
  const int polarity   = Polarity;
  const int pw         = PulseWidth;
  const int sensePH    = SensePulseHeight;
  const int sensePW    = SensePulseWidth;
  const int discharge  = ChannelDischargeTime;
  const Mode mode      = StimulationMode;

  for (ch = 0; ch < n; ch++) {
    hv513FastScan(ch);     //Select the electrode

    if (polarity == 0){    //Cathodic Stimulation
      gpio_fast_off(HV513_POL);
    } else {                 //Anodic Stimulation
      gpio_fast_on(HV513_POL);
    }
    // noInterrupts();            //Avoid interrupts during stimulation pulse. Might not necessary.
    PulseHeight = stim_pattern[ch];
    switch (mode) {
      case MONOPHASIC_STIMULATION:
        AD = monoPhasicPulse(PulseHeight, pw);
        break;
      case BIPHASIC_STIMULATION:
        AD = biPhasicPulse(PulseHeight, pw, PulseHeight, pw);
        break;
      default:
        AD = monoPhasicPulse(sensePH, sensePW);
        break;
    }

    // We only measure the voltage if the serial is not currently sending the voltage data to the PC
    if (!SendingVoltages) {
      voltage[ch * 2]     = (byte)(AD & 0xFF);
      voltage[ch * 2 + 1] = (byte)((AD >> 8) & 0xFF);
    }
    dischargeChannel(discharge); // Discharge the channel after stimulation
    // interrupts();
  }

  hv513Clear(HV513Num);  //It is to clear the HV513 outputs if any of the remaining electrodes are not stimulated.
  timerAlarmEnable(Timer1_Cfg);  // Re-enable the timer
}


void runEtactileKit() {
    /*Notes:*/
    //1. Static variables keep the parser state between loop iterations.
    //2. Payloads are parsed only once they have FULLY arrived (single size
    //   check instead of byte-by-byte accumulation). The largest payload
    //   (stim pattern = ElectrodeNum * 2 bytes) fits in every RX buffer, so
    //   the whole payload is applied in a few microseconds.
    static bool processingCommand = false; // Tracks if we are waiting for a command payload
    static int requiredBytes = 0;          // Payload size of the pending command
    static byte currentCommand = 0;        // The pending command
    static uint64_t commandStartUs = 0;    // When the pending command byte arrived (Timer2 ticks, 1us each)

    const uint64_t COMMAND_TIMEOUT_US = 2000000; // Payload must complete within this window

    bool madeProgress = false; // True if any bytes were consumed this call

    if (!processingCommand && isDataAvailable() > 0) {
        currentCommand = readInt_8(); // Read the command byte
        madeProgress = true;
        // Determine the number of required bytes based on the command
        switch (currentCommand) {
            case PC_ESP32_STIM_MODE:              requiredBytes = 1;                processingCommand = true; break;
            case PC_ESP32_STIM_PATTERN:           requiredBytes = ElectrodeNum * 2; processingCommand = true; break; // each electrode has a 16 bit pulse height value
            case PC_ESP32_STIMULATION_POLARITY:   requiredBytes = 1;                processingCommand = true; break;
            case PC_ESP32_STIMULATION_PULSE_WIDTH:requiredBytes = 2;                processingCommand = true; break;
            case PC_ESP32_SENSE_PULSE_HEIGHT:     requiredBytes = 1;                processingCommand = true; break;
            case PC_ESP32_SENSE_PULSE_WIDTH:      requiredBytes = 1;                processingCommand = true; break;
            case PC_ESP32_CHANNEL_DISCHARGE_TIME: requiredBytes = 1;                processingCommand = true; break;
            case PC_ESP32_STIMULATION_FREQUENCY:  requiredBytes = 2;                processingCommand = true; break;
            case PC_ESP32_ELECTRODE_NUM:          requiredBytes = 1;                processingCommand = true; break;
            
            case PC_ESP32_MEASURE_REQUEST: {
                // Send voltage[] while Timer1 is paused so the ISR cannot update
                // a two-byte sample halfway through the response.
                SendingVoltages = true;
                const int n = ElectrodeNum * 2;
                // timerAlarmDisable(Timer1_Cfg);
                writeBytes((const byte*)voltage, n);
                // timerAlarmEnable(Timer1_Cfg);
                SendingVoltages = false;
                return;
            }
            case PC_ESP32_HV513_NUM_REQUEST:
                // Disable stimulation timer: stackSense() drives the same HV513
                // GPIO pins (via hv513Init) that the ISR uses via hv513FastScan.
                timerAlarmDisable(Timer1_Cfg);
                writeInt_8(stackSense());
                timerAlarmEnable(Timer1_Cfg);
                return;
            case PC_ESP32_SYNC_CHECK:
                // This space can be configured to execute and return data for testing communication
                writeInt_8((byte)ElectrodeNum);
                return;
            default:
                // Unknown command, ignore
                currentCommand = 0;
                return; // Exit loop to avoid processing further in this cycle
            }
        commandStartUs = timerRead(Timer2_Cfg);
    }

    // Parse the payload once it has fully arrived
    if (processingCommand) {
        if (isDataAvailable() >= requiredBytes) {
            int rcv;
            switch (currentCommand) {
                case PC_ESP32_STIM_MODE:
                    rcv = readInt_8();
                    StimulationMode = (Mode)constrain(rcv, 0, 2);
                    break;
                case PC_ESP32_STIM_PATTERN:
                    for (int i = 0; i < requiredBytes / 2; i++) {
                        rcv = readInt_16();
                        stim_pattern[i] = constrain(rcv, 0, 4095); //All the 12 bits of the DAC are used for the pulse height. The constrain function can be used to limit the maximum pulse height.
                    }
                    break;
                case PC_ESP32_STIMULATION_POLARITY:
                    rcv = readInt_8();
                    Polarity = constrain(rcv, 0, 1); //Polarity (1 - anodic or 0 - cathodic)
                    break;
                case PC_ESP32_STIMULATION_PULSE_WIDTH:
                    PulseWidth = readInt_16();
                    break;
                case PC_ESP32_SENSE_PULSE_HEIGHT:
                    SensePulseHeight = readInt_8(); //All the 12 bits of the DAC are used for the pulse height. The constrain function can be used to limit the maximum pulse height.
                    break;
                case PC_ESP32_SENSE_PULSE_WIDTH:
                    SensePulseWidth = readInt_8();
                    break;
                case PC_ESP32_CHANNEL_DISCHARGE_TIME:
                    ChannelDischargeTime = readInt_8();
                    break;
                case PC_ESP32_STIMULATION_FREQUENCY: {
                    rcv = readInt_16();
                    if (rcv != 0) {
                        StimulationTimePeriod = 1000000.0/rcv; //convert the frequency to time period in us
                        setPeriodUs((uint32_t)StimulationTimePeriod); // Set the timer period
                    }
                    break;
                }
                case PC_ESP32_ELECTRODE_NUM:
                    rcv = readInt_8();
                    ElectrodeNum = constrain(rcv, 0, MAX_ELECTRODE_NUM);
                    break;
                default:
                    break;
            }
            processingCommand = false; // Command processing complete
            currentCommand = 0;
            madeProgress = true;
        } else if (timerRead(Timer2_Cfg) - commandStartUs > COMMAND_TIMEOUT_US) {
            // Payload never completed (PC disconnected / bytes dropped mid-command).
            // Abort and discard the partial payload so it is not misparsed as
            // new command bytes — otherwise the parser stays desynced forever.
            while (isDataAvailable() > 0) { readInt_8(); }
            processingCommand = false;
            currentCommand = 0;
        }
    }

    if (!madeProgress) {
        vTaskDelay(1); // Yield only when idle — back-to-back commands parse at full speed
    }
}
