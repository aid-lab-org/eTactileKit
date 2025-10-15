#include "etactilekit.h"

unsigned char stim_pattern[MAX_ELECTRODE_NUM] = {0};
unsigned int voltage[MAX_ELECTRODE_NUM] = { 0 };

// TaskHandle_t th[1];

hw_timer_t *Timer0_Cfg = NULL;   // Handle for the hardware timer
hw_timer_t *Timer1_Cfg = NULL;   // Handle for the hardware timer for the ADC

int Polarity                 = 1;    
int PulseHeight              = 0;    
int PulseWidth               = 0;
int SensePulseHeight         = 0;
int SensePulseWidth          = 0;
int ChannelDischargeTime     = 0;   
float StimulationTimePeriod  = 10000.0; // Time period for the stimulation in us - 1/frequency set to 100Hz by default

int ElectrodeNum             = 0;

void initEtactileKit() {
    initSwitching();
    initADC_DAC();
    initCommunication(BAUD_RATE);

    // start the timer
    Timer0_Cfg = timerBegin(0, 40, true); //(timer id, prescaler, count up) - look https://deepbluembedded.com/esp32-timers-timer-interrupt-tutorial-arduino-ide/

    // xTaskCreatePinnedToCore(stimulate,"stimulate", 4096, NULL, 3, &th[0], 1); //Task for stimulation. Higher priority than main void loop()
    Timer1_Cfg = timerBegin(1, 40, true);
    timerAttachInterrupt(Timer1_Cfg, &Timer1_Stimulate_ISR, true);
    timerAlarmWrite(Timer1_Cfg, (int)StimulationTimePeriod*2, true);
    timerAlarmEnable(Timer1_Cfg);
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

int monoPhasicPulse(int stim_pulse_height, int stim_pulse_width) {
  /*The DAAD pulse takes aroudn 6.6 to execute. The SPI values are written midway
  so the effective activation time is at around 3.3us*/
  int AD;
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

int biPhasicPulse(int height_a, int width_a, int height_b, int width_b) {
  int AD;
  // First phase:
  gpio_fast_on(HV513_POL); // Set the polarity to anodic
  monoPhasicPulse(height_a, width_a); // Call the function to generate a mono-phasic pulse

  // Second phase:
  gpio_fast_off(HV513_POL); // Set the polarity to cathodic
  AD = monoPhasicPulse(height_b, width_b); // Call the function to generate a mono-phasic pulse

  return AD; // Return the value read from the ADC
}

void dischargeChannel(int discharge_time) {
  DAAD(0);
  // POL = 1 and BL = 0 means all channels disabled (off)
  gpio_fast_on(HV513_POL);  // Set the polarity to ground
  gpio_fast_off(HV513_BL);  // Set the BL pin to low
  if (discharge_time > 7) {
    delay_exact_us(discharge_time - 7); // Delay for the pulse width
  }
  gpio_fast_on(HV513_BL);   // Reenable the HV513s
}

void stimulate(void *pvParameters)
{
  int AD, ch, DelayMsForStableLoop, activeTime;

  while(1){
    for (ch = 0; ch < ElectrodeNum; ch++) {
      hv513FastScan(ch); //select the electrode

      if(Polarity == 0){    //Cathodic Stimulation
        gpio_fast_off(HV513_POL);
      }else{                 //Anodic Stimulation
        gpio_fast_on(HV513_POL);
      }
    //   noInterrupts(); //avoid interrupts during stimulation pulse. Might not necessary.
        
      // if (stim_pattern[ch] != 0) {   //<---- This is the main part of the stimulation. If stim_pattern[ch] is 0, only the impedance is measured.
      //   DAAD(PulseHeight);
      //   if(PulseWidth<12){
      //     Step = 0;
      //   }else{
      //     Step = (int)((float)PulseWidth * 0.1244 - 1.1678);
      //   }
      //   for(t=0;t<Step;t++){         //<---- This loop is for the pulse width. The signal is hold until the calculated steps are looped.
      //     AD = DAAD(PulseHeight);
      //   }
      // }
      // else{
      //   DAAD(SensePulseHeight);     //write a pulse height to measure the impedance. This should be corrected for the changed DAC
      //   if(SensePulseWidth<12){
      //     Step = 0;
      //   }else{
      //     Step = (int)((float)SensePulseWidth * 0.1244 - 1.1678);
      //   }
      //   for(t=0;t<Step;t++){
      //     AD = DAAD(SensePulseHeight);
      //   }
      // }

      switch (stim_pattern[ch]) {
        case 1: // Mono-phasic stimulation
          AD = monoPhasicPulse(PulseHeight, PulseWidth);// Pulse
          activeTime += PulseWidth + ChannelDischargeTime;
          break;
        case 2: // Bi-phasic stimulation
          AD = biPhasicPulse(PulseHeight, PulseWidth, PulseHeight, PulseWidth);// Pulse
          activeTime += PulseWidth + PulseWidth + ChannelDischargeTime;
          break;
        default:
          // No stimulation, only impedance measurement
          AD = monoPhasicPulse(SensePulseHeight, SensePulseWidth); // Pulse
          break;
      }
      
      voltage[ch] = AD; // Store the voltage read from the ADC
      dischargeChannel(ChannelDischargeTime); // Discharge the channel after stimulation

    //   interrupts();
    }

    hv513Clear(HV513Num);             //It is to clear the HV513 outputs if any of the remaining electrodes are not stimulated.

    DelayMsForStableLoop = max(1000, (int)(StimulationTimePeriod - activeTime)); //activeTime in in us.

    delay_exact_us(DelayMsForStableLoop-1000); // Delay for the remaining time to complete the stimulation period (min 1ms)
    vTaskDelay(1); // Delay for the remaining time to complete the stimulation period
  }
}

void IRAM_ATTR Timer1_Stimulate_ISR() { // Timer interrupt service routine
  timerAlarmDisable(Timer1_Cfg); // Disable the timer to prevent re-entrancy if the stimulation takes longer than the timer period

  int AD, ch, activeTime = 0;               // Variable to track the active time for the stimulation
  
  for (ch = 0; ch < ElectrodeNum; ch++) {
    hv513FastScan(ch);     //Select the electrode
    
    if(Polarity == 0){     //Cathodic Stimulation
      gpio_fast_off(HV513_POL);
    }else{                 //Anodic Stimulation
      gpio_fast_on(HV513_POL);
    }
    // noInterrupts();            //Avoid interrupts during stimulation pulse. Might not necessary.
    switch (stim_pattern[ch]) {
      case 1: // Mono-phasic stimulation
        AD = monoPhasicPulse(PulseHeight, PulseWidth);// Pulse
        activeTime += PulseWidth + ChannelDischargeTime;
        break;
      case 2: // Bi-phasic stimulation
        AD = biPhasicPulse(PulseHeight, PulseWidth, PulseHeight, PulseWidth);// Pulse
        activeTime += PulseWidth + PulseWidth + ChannelDischargeTime;
        break;
      default:
        // No stimulation, only impedance measurement
        AD = monoPhasicPulse(SensePulseHeight, SensePulseWidth); // Pulse
        break;
    }

    voltage[ch] = AD; // Store the voltage read from the ADC
    dischargeChannel(ChannelDischargeTime); // Discharge the channel after stimulation
    // interrupts();
  }

  hv513Clear(HV513Num);               //It is to clear the HV513 outputs if any of the remaining electrodes are not stimulated.

  timerAlarmEnable(Timer1_Cfg);       // Re-enable the timer
}


void runEtactileKit() {
    /*Notes:*/
    //1. Use of static variables to track the state of the command processing in the loop without being reset at each iteration.
    static bool processingCommand = false; // Tracks if we are in the middle of processing a command
    static int bytesRead = 0;              // Tracks the number of bytes read for the current command
    static int requiredBytes = 0;          // Tracks the total bytes needed for the current command
    static byte currentCommand = 0;        // Tracks the currently active command

    int rcv = 0; // Variable to store the received values

    if (!processingCommand && isDataAvailable() > 0) {
        currentCommand = readInt_8(); // Read the command byte
        // Determine the number of required bytes based on the command
        switch (currentCommand) {
          case PC_ESP32_STIM_PATTERN:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = ElectrodeNum; // stim_pattern
              break;
          case PC_ESP32_STIMULATION_POLARITY:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 1; // Polarity
              break;
          case PC_ESP32_STIMULATION_PULSE_HEIGHT:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 2; // PulseHeight
              break;
          case PC_ESP32_STIMULATION_PULSE_WIDTH:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 2; // PulseWidth
              break;
          case PC_ESP32_SENSE_PULSE_HEIGHT:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 1; // PulseHeight
              break;
          case PC_ESP32_SENSE_PULSE_WIDTH:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 1; // PulseWidth
              break;
          case PC_ESP32_CHANNEL_DISCHARGE_TIME:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 1; // Discharge time
              break;
          case PC_ESP32_STIMULATION_FREQUENCY:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 2; // Frequency
              break;
          case PC_ESP32_ELECTRODE_NUM:
              processingCommand = true;
              bytesRead = 0;
              requiredBytes = 1; // Electrode number
              break;
          case PC_ESP32_MEASURE_REQUEST:
              for (int ch = 0; ch < ElectrodeNum; ch++){
                writeInt_16(voltage[ch]);
              }
              return; // Exit loop to avoid processing further in this cycle
          case PC_ESP32_HV513_NUM_REQUEST:
              writeInt_8(stackSense());
              return; // Exit loop to avoid processing further in this cycle
          default:
              // Unknown command, ignore
              currentCommand = 0;
              return; // Exit loop to avoid processing further in this cycle
          }
    }

    // Process the command bytes
    if (processingCommand) {
        while (isDataAvailable() > 0 && bytesRead < requiredBytes) { //The inequality make sure that we don't read more than required bytes
            switch (currentCommand) { 
                case PC_ESP32_STIM_PATTERN:
                    rcv = readInt_8();
                    stim_pattern[bytesRead] = rcv;
                    bytesRead++;
                    break;
                case PC_ESP32_STIMULATION_POLARITY:
                    rcv = readInt_8();
                    Polarity = constrain(rcv, 0, 1); //Polarity (1 - anodic or 0 - cathodic)
                    bytesRead++;
                    break;
                case PC_ESP32_STIMULATION_PULSE_HEIGHT:
                    if (isDataAvailable() >= 2) { // Check if data is available before reading
                        rcv = readInt_16();
                        PulseHeight = constrain(rcv, 0, 4095); //All the 12 bits of the DAC are used for the pulse height
                        // constrain value can be used to limit the maximum pulse height
                        bytesRead += 2;
                    }
                    break;
                case PC_ESP32_STIMULATION_PULSE_WIDTH:
                    if (isDataAvailable() >= 2) { // Check if data is available before reading
                        rcv = readInt_16();
                        if (rcv != 0){
                            PulseWidth = rcv; //pulse width
                        }
                        bytesRead += 2;
                    }
                    break;
                case PC_ESP32_SENSE_PULSE_HEIGHT:
                    rcv = readInt_8() << 2; //The 8 bit pulse height is shifted by 2 bits to the left for the 12 bit DAC. (That is we are using only using 1/4th of the 12 bit DAC)
                    SensePulseHeight = rcv;
                    bytesRead++;
                    break;
                case PC_ESP32_SENSE_PULSE_WIDTH:
                    rcv = readInt_8();
                    SensePulseWidth = rcv; //pulse width
                    bytesRead++;
                    break;
                case PC_ESP32_CHANNEL_DISCHARGE_TIME:
                    rcv = readInt_8();
                    ChannelDischargeTime = rcv; //discharge time
                    bytesRead++;
                    break;
                case PC_ESP32_STIMULATION_FREQUENCY:
                    if (isDataAvailable() >= 2) { // Check if data is available before reading
                        rcv = readInt_16();
                        if (rcv != 0){
                            StimulationTimePeriod = 1000000.0/rcv; //convert the frequency to time period in us
                            setPeriodUs((uint32_t)StimulationTimePeriod); // Set the timer period
                        }
                        bytesRead += 2;
                    }
                    break;
                case PC_ESP32_ELECTRODE_NUM:
                    rcv = readInt_8();
                    ElectrodeNum = constrain(rcv, 0, MAX_ELECTRODE_NUM);
                    bytesRead++;
                    break;
                default: // Ignore other commands if not included in the switch case
                    break;
            }

            // Check if the entire command has been processed
            if (bytesRead == requiredBytes) {
                // writeByte(ESP32_PC_RECEIVE_FINISHED);  //Send 0xFE to indicate that the command has been received properly
                processingCommand = false;             // Command processing complete
                currentCommand = 0;                    // Reset current command
            }
        }
    }
    vTaskDelay(1); // Added for stability
}