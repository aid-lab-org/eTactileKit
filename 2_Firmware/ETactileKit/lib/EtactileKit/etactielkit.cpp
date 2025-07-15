#include "etactilekit.h"

unsigned char stim_pattern[MAX_ELECTRODE_NUM] = {0};
unsigned char voltage[MAX_ELECTRODE_NUM] = { 0 };

TaskHandle_t th[1];

int Polarity                 = 1;    
int PulseHeight              = 0;    
int PulseWidth               = 0;
int SensePulseHeight         = 0;
int SensePulseWidth          = 0;
int ChannelDischargeTime     = 0;   
float StimulationTimePeriod  = 13.3;

int ElectrodeNum             = 0;

void initEtactileKit() {
    initSwitching();
    initADC_DAC();
    initCommunication(BAUD_RATE);

    stackSense();
    xTaskCreatePinnedToCore(stimulate,"stimulate", 4096, NULL, 3, &th[0], 1); //Task for stimulation. Higher priority than main void loop()
}

void stimulate(void *pvParameters)
{
  int ch, t,Step,DelayMsForStableLoop;
  short AD;
  
  while(1){
    for (ch = 0; ch < ElectrodeNum; ch++) {
      hv513FastScan(ch); //select the electrode

      if(Polarity == 0){    //Cathodic Stimulation
        digitalWrite(HV513_POL, LOW);
      }else{                 //Anodic Stimulation
        digitalWrite(HV513_POL, HIGH);
      }
      noInterrupts(); //avoid interrupts during stimulation pulse. Might not necessary.
        
      if (stim_pattern[ch] != 0) {   //<---- This is the main part of the stimulation. If stim_pattern[ch] is 0, only the impedance is measured.
        DAAD(PulseHeight);
        if(PulseWidth<12){
          Step = 0;
        }else{
          Step = (int)((float)PulseWidth * 0.1244 - 1.1678);
        }
        for(t=0;t<Step;t++){         //<---- This loop is for the pulse width. The signal is hold until the calculated steps are looped.
          AD = DAAD(PulseHeight);
        }
      }
      else{
        DAAD(SensePulseHeight);     //write a pulse height to measure the impedance. This should be corrected for the changed DAC
        if(SensePulseWidth<12){
          Step = 0;
        }else{
          Step = (int)((float)SensePulseWidth * 0.1244 - 1.1678);
        }
        for(t=0;t<Step;t++){
          AD = DAAD(SensePulseHeight);
        }
      }
      
      AD = DAAD(0);                 // Turning the current off and measuring the voltage for impedance calculation.
      voltage[ch] = AD>>4;          // Record voltage(12bit data to 8bit data conversion). To calculate impedance, divide this by current.

      digitalWrite(HV513_POL, HIGH);//(POL=1 & BL=0 means ALL GND)
      digitalWrite(HV513_BL, LOW);
      Step = (int)((float)ChannelDischargeTime * 0.1244 - 1.1678);
      for(t=0;t<Step;t++){
        AD = DAAD(0);
      }
      digitalWrite(HV513_BL, HIGH); 
      interrupts();
    }

    hv513Clear(HV513Num);             //It is to clear the HV513 outputs if any of the remaining electrodes are not stimulated.
    DelayMsForStableLoop = (int)(StimulationTimePeriod - ElectrodeNum*(PulseWidth + ChannelDischargeTime)/1000.0); //13.3ms is for 60Hz loop. StimNum*0.2 is stimulation time.
    if(DelayMsForStableLoop>1){
      vTaskDelay(DelayMsForStableLoop); //Delay time for freeRTOS
    }else{
      vTaskDelay(1); //At least 1ms delay is necessary for freeRTOS (to avoid watchdog bark)
    }
  }
}

void runEtactileKit() {
    /*Notes:*/
    //1. Use of static variables to track the state of the command processing in the loop without being reset at each iteration.
    static bool processingCommand = false; // Tracks if we are in the middle of processing a command
    static int bytesRead = 0;              // Tracks the number of bytes read for the current command
    static int requiredBytes = 0;          // Tracks the total bytes needed for the current command
    static char currentCommand = 0;        // Tracks the currently active command

    if (!processingCommand && isDataAvailable() > 0) {
        currentCommand = readByte(); // Read the command byte
        // Determine the number of required bytes based on the command
        switch (currentCommand) {
        case PC_ESP32_STIM_PATTERN:
            processingCommand = true;
            bytesRead = 0;
            requiredBytes = ElectrodeNum; // PulseHeight, PulseWidth, and stim_pattern
            break;
        case PC_ESP32_STIMULATION_POLARITY:
            processingCommand = true;
            bytesRead = 0;
            requiredBytes = 1; // Polarity
            break;
        case PC_ESP32_STIMULATION_PULSE_HEIGHT:
            processingCommand = true;
            bytesRead = 0;
            requiredBytes = 1; // PulseHeight
            break;
        case PC_ESP32_STIMULATION_PULSE_WIDTH:
            processingCommand = true;
            bytesRead = 0;
            requiredBytes = 1; // PulseWidth
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
            requiredBytes = 1; // Frequency
            break;
        case PC_ESP32_ELECTRODE_NUM:
            processingCommand = true;
            bytesRead = 0;
            requiredBytes = 1; // Electrode number
            break;
        case PC_ESP32_MEASURE_REQUEST:
            for (int ch = 0; ch < ElectrodeNum; ch++){
            writeByte(voltage[ch]);
            }
            return; // Exit loop to avoid processing further in this cycle
        case PC_ESP32_HV513_NUM_REQUEST:
            writeByte(stackSense());
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
            char rcv = readByte();
            switch (currentCommand) { 
                case PC_ESP32_STIM_PATTERN:
                    stim_pattern[bytesRead] = rcv;
                    break;
                case PC_ESP32_STIMULATION_POLARITY:
                    Polarity = constrain(rcv, 0, 1); //Polarity (1 - anodic or 0 - cathodic)
                    break;
                case PC_ESP32_STIMULATION_PULSE_HEIGHT:
                    PulseHeight = constrain(rcv, 0, 250) << 2; //The 8 bit pulse height is shifted by 2 bits to the left for the 12 bit DAC. (That is we are using only using 1/4th of the 12 bit DAC)
                    break;
                case PC_ESP32_STIMULATION_PULSE_WIDTH:
                    PulseWidth = constrain(rcv, 0, 250);       //pulse width (0 to 250)
                    break;
                case PC_ESP32_SENSE_PULSE_HEIGHT:
                    SensePulseHeight = constrain(rcv, 0, 250) << 2; //The 8 bit pulse height is shifted by 2 bits to the left for the 12 bit DAC. (That is we are using only using 1/4th of the 12 bit DAC)
                    break;
                case PC_ESP32_SENSE_PULSE_WIDTH:
                    SensePulseWidth = constrain(rcv, 0, 250); //pulse width (0 to 250)
                    break;
                case PC_ESP32_CHANNEL_DISCHARGE_TIME:
                    ChannelDischargeTime = constrain(rcv, 0, 250); //discharge time (0 to 250)
                    break;
                case PC_ESP32_STIMULATION_FREQUENCY:
                    if (rcv != 0){
                        StimulationTimePeriod = round(1000.0/constrain(rcv, 1, 250)); //convert the frequency to time period (0 to 250)
                    }
                    break;
                case PC_ESP32_ELECTRODE_NUM:
                    ElectrodeNum = constrain(rcv, 0, MAX_ELECTRODE_NUM); //praneeth
                    break;
                default: // Ignore other commands if not included in the switch case
                    break;
            }
            bytesRead++;

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