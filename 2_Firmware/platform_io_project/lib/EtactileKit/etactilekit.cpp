#include "etactilekit.h"
#include "esp_timer.h"

/************************************************************************* */
/*Work split between the cores                                             */
/*Core 1 runs the stimulation interrupt (Timer1). The other interrupts     */
/*there are the FreeRTOS tick, the cross-core task wake-up and the         */
/*interrupt watchdog, and the tasks on core 1 (Arduino loop(), the WiFi    */
/*event task) run between scans. Host communication and command           */
/*parsing run in a task on core 0, beside the WiFi stack. The timer driver */
/*holds Timer1's lock for the whole of a scan and the pulse busy-wait polls*/
/*Timer0 throughout it, so the command task never calls a hardware-timer   */
/*function: frequency changes are applied by the interrupt.                */
/************************************************************************* */
#define COMMAND_TASK_CORE      0
#define COMMAND_TASK_PRIORITY  5        // Above the UDP discovery (3) and mDNS (1) tasks, below the network stack
#define COMMAND_TASK_STACK     8192
#define COMMAND_TIMEOUT_US     2000000  // A command's payload must complete within this window
#define COMMAND_MAX_BUSY_US    20000    // The command task sleeps a tick when it has not for this long (checked between parser steps)
#define SCAN_HOLD_TIMEOUT_US   500000   // Longest an HV513 count request waits for the scan in progress
#define DEFAULT_PERIOD_US      10000    // 100 Hz until the host sets a frequency

// scanOwner values. The interrupt takes the scan for its duration; the command task takes it while
// stackSense() drives the HV513 pins that a scan uses.
#define SCAN_FREE              0
#define SCAN_RUNNING           1
#define SCAN_HELD              2

hw_timer_t *Timer0_Cfg = NULL;   // Busy-wait timer for the pulse timing (0.5 us ticks)
hw_timer_t *Timer1_Cfg = NULL;   // Stimulation timer; each alarm runs one scan (0.5 us ticks)

volatile int Polarity                 = 1;
volatile Mode StimulationMode         = MONOPHASIC_STIMULATION;
volatile int PulseWidth               = 0;
volatile int SensePulseHeight         = 0;
volatile int SensePulseWidth          = 0;
volatile int ChannelDischargeTime     = 0;

volatile int ElectrodeNum             = 0;

// Stimulation pattern, handed from the command task to the interrupt through a lock-free triple
// buffer. The task fills the back buffer and swaps it with the middle one; at the start of a scan
// the interrupt swaps its front buffer with the middle one if that holds a newer pattern. Each swap
// is one atomic exchange, so a scan always uses one complete pattern and never waits for the task.
struct Pattern {
    int count;                                  // Electrodes scanned
    uint16_t height[MAX_ELECTRODE_NUM];         // Pulse height of each electrode
};
#define PATTERN_FRESH 0x100                     // patternMiddle flag: published, not yet taken by the interrupt
static Pattern patterns[3];
static volatile uint32_t patternMiddle = 1;     // Middle buffer index, plus PATTERN_FRESH
static int patternBack = 2;                     // Command task only
static int patternFront = 0;                    // Interrupt only
static uint16_t stimHeight[MAX_ELECTRODE_NUM];  // Command task only: heights as the host last set them

// Written by the command task, read by the interrupt
static volatile int PolarityPending = 1;        // Copied to Polarity at the start of the next scan
static volatile uint32_t alarmTicksPending = DEFAULT_PERIOD_US * 2;
static volatile uint32_t scanOwner = SCAN_FREE;
static volatile bool scanHoldRequest = false;   // The interrupt starts no scan while this is set

// Written by the interrupt, read by the command task: last ADC reading of each channel
static volatile uint16_t voltage[MAX_ELECTRODE_NUM] = {0};

static uint32_t alarmTicks = DEFAULT_PERIOD_US * 2;  // Interrupt only: period programmed into Timer1

static void commandTask(void *);

void initEtactileKit() {
    initSwitching();
    initADC_DAC();

    Timer0_Cfg = timerBegin(0, 40, true); // (timer id, prescaler, count up): 80 MHz / 40, 0.5 us ticks

    // The interrupt is allocated on the calling core, so setup() must run on core 1 (the Arduino default).
    Timer1_Cfg = timerBegin(1, 40, true);
    timerAttachInterrupt(Timer1_Cfg, &Timer1_Stimulate_ISR, true);
    timerAlarmWrite(Timer1_Cfg, alarmTicks, true);
    timerAlarmEnable(Timer1_Cfg);

    xTaskCreatePinnedToCore(commandTask, "etk_commands", COMMAND_TASK_STACK, NULL,
                            COMMAND_TASK_PRIORITY, NULL, COMMAND_TASK_CORE);
}

void IRAM_ATTR delay_exact_us(int us) {
  if (us < 3) {
    us = 3; // minimum delay
  }
  us = (int)(us * 2.0 - 5.4); // 2.0*us - 5.4

  timerRestart(Timer0_Cfg);
  while (timerRead(Timer0_Cfg) < us);
}

void setPeriodUs(uint32_t us)
{
    alarmTicksPending = us*2;  // *2 because the tick time is 0.5us--> 40/80MHz. Applied by the interrupt.
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

  // While the command task senses the HV513 stack on the same pins (and while it waits to), no
  // scan starts; those periods are skipped.
  uint32_t owner = SCAN_FREE;
  if (!scanHoldRequest &&
      __atomic_compare_exchange_n(&scanOwner, &owner, SCAN_RUNNING, false, __ATOMIC_ACQUIRE, __ATOMIC_RELAXED)) {
    if (patternMiddle & PATTERN_FRESH) {  // Take the pattern the task published last
      patternFront = __atomic_exchange_n(&patternMiddle, (uint32_t)patternFront, __ATOMIC_ACQ_REL) & ~PATTERN_FRESH;
    }
    const Pattern &pattern = patterns[patternFront];
    Polarity = PolarityPending;  // biPhasicPulse() reads Polarity, so it only changes between scans

    int AD, ch, PulseHeight;
    const int n          = pattern.count;
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
      PulseHeight = pattern.height[ch];
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

      voltage[ch] = AD;  // One 16-bit store, so the command task never reads half a sample
      dischargeChannel(discharge); // Discharge the channel after stimulation
    }

    hv513Clear(HV513Num);  //It is to clear the HV513 outputs if any of the remaining electrodes are not stimulated.
    __atomic_store_n(&scanOwner, SCAN_FREE, __ATOMIC_RELEASE);
  }

  // A new period is programmed here, between scans, and counts from the start of this scan.
  const uint32_t ticks = alarmTicksPending;
  if (ticks != alarmTicks) {
    alarmTicks = ticks;
    timerAlarmWrite(Timer1_Cfg, ticks, true);
  }
  timerAlarmEnable(Timer1_Cfg);  // Re-enable the timer
}


// Hands stimHeight[0..ElectrodeNum) to the interrupt, which uses it from its next scan on.
static void publishPattern() {
    Pattern &next = patterns[patternBack];
    next.count = ElectrodeNum;
    memcpy(next.height, stimHeight, ElectrodeNum * sizeof(uint16_t));
    patternBack = __atomic_exchange_n(&patternMiddle, (uint32_t)patternBack | PATTERN_FRESH, __ATOMIC_ACQ_REL) & ~PATTERN_FRESH;
}


// Every output amplitude back to zero: all stimulation pulse heights and the sense pulse height.
// The framing parameters (electrode number, pulse widths, ...) are kept so the payload sizes the
// next host sends still parse correctly.
static void stopStimulation() {
    memset(stimHeight, 0, sizeof(stimHeight));
    publishPattern();
    SensePulseHeight = 0;
}


// One parser step: handles at most one command. Returns true if it did any work or serial data is
// still arriving, so the task polls again at once instead of sleeping.
static bool processCommands() {
    /*Notes:*/
    //1. Static variables keep the parser state between iterations of the command task.
    //2. Payloads are parsed only once they have FULLY arrived (single size
    //   check instead of byte-by-byte accumulation). The largest payload
    //   (stim pattern = ElectrodeNum * 2 bytes) fits in every RX buffer, so
    //   the whole payload is applied in a few microseconds.
    //3. Whenever a host connects or disconnects, stimulation stops and the
    //   parser restarts on a command boundary, so a dropped host can never
    //   leave electrodes stimulating or half a command pending. A serial port
    //   reopened within SERIAL_LINK_TIMEOUT_MS counts as the same connection.
    static bool processingCommand = false; // Tracks if we are waiting for a command payload
    static int requiredBytes = 0;          // Payload size of the pending command
    static byte currentCommand = 0;        // The pending command
    static int64_t commandStartUs = 0;     // When the pending command byte arrived
    static uint32_t knownLinkGeneration = 0; // linkGeneration the parser state belongs to

    bool madeProgress = false; // True if any bytes were consumed this call

    const bool receiving = serviceCommunication();
    if (linkGeneration != knownLinkGeneration) {
        knownLinkGeneration = linkGeneration;
        stopStimulation();
        processingCommand = false;
        currentCommand = 0;
    }

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
                // Low byte first, two bytes per electrode. Each sample is copied with one 16-bit
                // load; samples may come from consecutive scans.
                uint16_t readings[MAX_ELECTRODE_NUM];
                const int n = ElectrodeNum;
                for (int i = 0; i < n; i++) {
                    readings[i] = voltage[i];
                }
                writeBytes((const byte*)readings, n * 2);
                return true;
            }
            case PC_ESP32_HV513_NUM_REQUEST: {
                // stackSense() drives the HV513 pins a scan uses: stop new scans, wait for the one
                // in progress to finish, sense, then let scans resume.
                scanHoldRequest = true;
                const int64_t holdStartUs = esp_timer_get_time();
                uint32_t owner = SCAN_FREE;
                bool held;
                while (!(held = __atomic_compare_exchange_n(&scanOwner, &owner, SCAN_HELD, false,
                                                            __ATOMIC_ACQUIRE, __ATOMIC_RELAXED))) {
                    if (esp_timer_get_time() - holdStartUs >= SCAN_HOLD_TIMEOUT_US) break;
                    owner = SCAN_FREE;
                    vTaskDelay(1);
                    sampleHostPresence();
                }
                byte count = (byte)HV513Num;  // The last count sensed, if the scan never ended
                if (held) {
                    count = stackSense();
                    __atomic_store_n(&scanOwner, SCAN_FREE, __ATOMIC_RELEASE);
                }
                scanHoldRequest = false;
                writeInt_8(count);
                return true;
            }
            case PC_ESP32_SYNC_CHECK:
                // This space can be configured to execute and return data for testing communication
                writeInt_8((byte)ElectrodeNum);
                return true;
            default:
                // Unknown command, ignore
                currentCommand = 0;
                return true;
            }
        commandStartUs = esp_timer_get_time();
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
                        stimHeight[i] = constrain(rcv, 0, 4095); //All the 12 bits of the DAC are used for the pulse height. The constrain function can be used to limit the maximum pulse height.
                    }
                    publishPattern();
                    break;
                case PC_ESP32_STIMULATION_POLARITY:
                    rcv = readInt_8();
                    PolarityPending = constrain(rcv, 0, 1); //Polarity (1 - anodic or 0 - cathodic)
                    break;
                case PC_ESP32_STIMULATION_PULSE_WIDTH:
                    PulseWidth = readInt_16();
                    break;
                case PC_ESP32_SENSE_PULSE_HEIGHT:
                    SensePulseHeight = readInt_8(); //One byte: 0-255 of the 12-bit DAC range
                    break;
                case PC_ESP32_SENSE_PULSE_WIDTH:
                    SensePulseWidth = readInt_8();
                    break;
                case PC_ESP32_CHANNEL_DISCHARGE_TIME:
                    ChannelDischargeTime = readInt_8();
                    break;
                case PC_ESP32_STIMULATION_FREQUENCY:
                    rcv = readInt_16();
                    if (rcv != 0) {
                        setPeriodUs(1000000 / rcv); //convert the frequency to time period in us
                    }
                    break;
                case PC_ESP32_ELECTRODE_NUM: {
                    rcv = readInt_8();
                    const int n = constrain(rcv, 0, MAX_ELECTRODE_NUM);
                    // Channels joining the scan start at zero, not at whatever they last held.
                    for (int i = ElectrodeNum; i < n; i++) {
                        stimHeight[i] = 0;
                    }
                    ElectrodeNum = n;
                    publishPattern();
                    break;
                }
                default:
                    break;
            }
            processingCommand = false; // Command processing complete
            currentCommand = 0;
            madeProgress = true;
        } else if (esp_timer_get_time() - commandStartUs > COMMAND_TIMEOUT_US) {
            // Payload never completed (PC disconnected / bytes dropped mid-command).
            // Abort and discard the partial payload so it is not misparsed as
            // new command bytes — otherwise the parser stays desynced forever.
            while (isDataAvailable() > 0) { readInt_8(); }
            processingCommand = false;
            currentCommand = 0;
        }
    }

    return madeProgress || receiving;
}


// Runs the host link and the command parser on core 0. When idle it sleeps until serial data
// arrives or a tick passes. Unless it slept a whole tick within the last COMMAND_MAX_BUSY_US
// (continuous traffic, or a refused host streaming data), it sleeps a tick anyway, so the
// lower-priority tasks and the watched idle task on this core keep running.
static void commandTask(void *) {
    initCommunication();
    int64_t lastSleepUs = esp_timer_get_time();
    for (;;) {
        const bool busy = processCommands();
        if (esp_timer_get_time() - lastSleepUs >= COMMAND_MAX_BUSY_US) {
            vTaskDelay(1);
            lastSleepUs = esp_timer_get_time();
        } else if (!busy && !waitForHostData()) {
            lastSleepUs = esp_timer_get_time();
        }
    }
}
