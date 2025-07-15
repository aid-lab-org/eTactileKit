using UnityEngine;
using System.Collections;
using System.Collections.Generic;

/// <summary>
/// The main MonoBehaviour class for controlling the ETactileKit device via serial communication.
/// Provides properties and methods to configure stimulation parameters (e.g., pulse width/height, frequency),
/// manage electrode counts, retrieve sensor data (voltages), and ensure parameter safety.
/// </summary>
public class ETactileKit : MonoBehaviour
{
    /// <summary>
    /// The name of the serial port to use (e.g., "COM5", "/dev/ttyUSB0").
    /// </summary>
    public string portName = "COM5";

    /// <summary>
    /// The baud rate for the serial communication (e.g., 921600).
    /// </summary>
    public int baudRate = 921600;

    /// <summary>
    /// The read timeout in milliseconds. This defines how long the program will wait
    /// for a response when reading data from the serial port.
    /// </summary>
    private int readTimeout = 5;

    /// <summary>
    /// The write timeout in milliseconds. This defines how long the program will wait
    /// when sending data to the serial port before timing out.
    /// </summary>
    private int writeTimeout = 5;

    /// <summary>
    /// The <see cref="SerialHandler"/> instance responsible for handling
    /// all serial port operations for this device.
    /// </summary>
    private SerialHandler serialHandler;    // Class-level reference for handler1
    //private Queue<SerialCommandExecutor> commandQueue = new Queue<SerialCommandExecutor>();

    /// <summary>
    /// The polarity for stimulation. 
    /// Valid values: 
    ///  - <c>1</c> for Anodic
    ///  - <c>0</c> for Cathodic
    /// </summary>
    private int polarity;

    /// <summary>
    /// Gets or sets the polarity of the stimulation.
    /// Setting this property sends the polarity change to the device immediately.
    /// </summary>
    public int Polarity
    {
        get => polarity;
        set
        {
            polarity = value;
            SendStimulationPolarity(value);
        }
    }

    /// <summary>
    /// Tracks the number of electrodes configured for the device.
    /// Setting this property updates the device with the new electrode count.
    /// </summary>
    private int numberOfElectrodes;

    /// <summary>
    /// Gets or sets the number of electrodes.
    /// Setting this property sends the updated electrode number to the device.
    /// </summary>
    public int NumberOfElectrodes
    {
        get => numberOfElectrodes;
        set
        {
            numberOfElectrodes = value;
            SendElectrodeNumber(value);
        }
    }

    /// <summary>
    /// The pulse height (amplitude) for stimulation in arbitrary units.
    /// Setting this property updates the device's stimulation pulse height.
    /// </summary>
    private int stimulationPulseHeight;

    /// <summary>
    /// Gets or sets the stimulation pulse height.
    /// Setting this property sends the updated pulse height to the device.
    /// </summary>
    public int StimulationPulseHeight
    {
        get => stimulationPulseHeight;
        set
        {
            stimulationPulseHeight = value;
            SendStimulationPulseHeight(value);
        }
    }

    /// <summary>
    /// The pulse width (in microseconds or device-dependent units) for stimulation.
    /// Setting this property updates the device's stimulation pulse width.
    /// </summary>
    private int stimulationPulseWidth;

    /// <summary>
    /// Gets or sets the stimulation pulse width.
    /// Setting this property sends the updated pulse width to the device.
    /// </summary>
    public int StimulationPulseWidth
    {
        get => stimulationPulseWidth;
        set
        {
            stimulationPulseWidth = value;
            SendStimulationPulseWidth(value);
        }
    }

    /// <summary>
    /// The pulse height (amplitude) used for sensing/measurement. 
    /// Setting this property updates the device's sense pulse height.
    /// </summary>
    private int sensePulseHeight;

    /// <summary>
    /// Gets or sets the sense pulse height.
    /// Setting this property sends the updated sense pulse height to the device.
    /// </summary>
    public int SensePulseHeight
    {
        get => sensePulseHeight;
        set
        {
            sensePulseHeight = value;
            SendSensePulseHeight(value);
        }
    }

    /// <summary>
    /// The pulse width (in microseconds or device-dependent units) used for sensing/measurement.
    /// Setting this property updates the device's sense pulse width.
    /// </summary>
    private int sensePulseWidth;

    /// <summary>
    /// Gets or sets the sense pulse width.
    /// Setting this property sends the updated sense pulse width to the device.
    /// </summary>
    public int SensePulseWidth
    {
        get => sensePulseWidth;
        set
        {
            sensePulseWidth = value;
            SendSensePulseWidth(value);
        }
    }

    /// <summary>
    /// The discharge time (in milliseconds or device-dependent units) for each channel after stimulation.
    /// Setting this property updates the device's discharge time.
    /// </summary>  
    private int channelDischargeTime;

    /// <summary>
    /// Gets or sets the channel discharge time.
    /// Setting this property sends the updated channel discharge time to the device.
    /// </summary>
    public int ChannelDischargeTime
    {
        get => channelDischargeTime;
        set
        {
            channelDischargeTime = value;
            SendChannelDischargeTime(value);
        }
    }

    /// <summary>
    /// The frequency of stimulation (in Hz or device-dependent units).
    /// Setting this property updates the device's stimulation frequency.
    /// </summary>
    private int stimulationFrequency;

    /// <summary>
    /// Gets or sets the stimulation frequency.
    /// Setting this property sends the updated stimulation frequency to the device.
    /// </summary>
    public int StimulationFrequency
    {
        get => stimulationFrequency;
        set
        {
            stimulationFrequency = value;
            SendStimulationFrequency(value);
        }
    }

    /// <summary>
    /// The current stimulation pattern, typically an array where each element 
    /// represents the intensity/enable state for a given electrode.
    /// </summary>
    private int[] stimulationPattern;      // Array to store the stimulation pattern

    /// <summary>
    /// Gets or sets the stimulation pattern.
    /// Setting this property sends the updated stimulation pattern to the device.
    /// </summary>
    public int[] StimulationPattern
    {
        get => stimulationPattern;
        set
        {
            stimulationPattern = value;
            SendStimulationPattern(value);
        }
    }

    /// <summary>
    /// The number of HV513 chips (shift registers) detected by the device.
    /// A property read triggers an update request to the hardware.
    /// </summary>
    private int hv513Number;

    /// <summary>
    /// Gets the current HV513 count from the device.
    /// Accessing this property sends a command to the device and updates
    /// <see cref="hv513Number"/> with the returned value.
    /// </summary>
    public int Hv513Number
    {
        get
        {
            UpdateAndGetHV513Count();
            return hv513Number;
        }
    }

    /// <summary>
    /// Stores the electrode mapping as an array of ints (the meaning depends on hardware usage). mapping[0] means which channel is used for the first electrode in the application ans so on.
    /// This property setter does not immediately send anything to the device.
    /// </summary>
    private int[] electrodeMapping;

    /// <summary>
    /// Gets or sets the electrode mapping.
    /// This value is stored locally and not immediately sent to the device.
    /// </summary>
    public int[] ElectrodeMapping
    {
        get => electrodeMapping;
        set
        {
            electrodeMapping = value;
        }
    }

    /// <summary>
    /// Stores the voltage readings from the electrodes. 
    /// Reading from this property triggers a voltage reading command to the device.
    /// </summary>
    private int[] voltages;

    /// <summary>
    /// Gets the most recent voltage readings from the device.
    /// Accessing this property sends a read request to the device 
    /// and populates <see cref="voltages"/> with the results.
    /// </summary>
    public int[] Voltages
    {
        get
        {
            GetVoltageReadings();
            return voltages;
        }
    }

    //----------------------------------------------------------------------------------------------//
    // Constants representing specific command bytes for the protocol communication with the ESP32.
    //----------------------------------------------------------------------------------------------//
    private const byte PC_ESP32_MEASURE_REQUEST = 0xFF;
    private const byte PC_ESP32_STIM_PATTERN = 0xFE;
    private const byte PC_ESP32_STIMULATION_POLARITY = 0xFD;
    private const byte PC_ESP32_ELECTRODE_NUM = 0xFC;
    private const byte PC_ESP32_STIMULATION_PULSE_HEIGHT = 0xFB;
    private const byte PC_ESP32_STIMULATION_PULSE_WIDTH = 0xFA;
    private const byte PC_ESP32_SENSE_PULSE_HEIGHT = 0xF9;
    private const byte PC_ESP32_SENSE_PULSE_WIDTH = 0xF8;
    private const byte PC_ESP32_CHANNEL_DISCHARGE_TIME = 0xF7;
    private const byte PC_ESP32_STIMULATION_FREQUENCY = 0xF6;
    private const byte PC_ESP32_HV513_NUM_REQUEST = 0xF5;

    // private const byte ESP32_PC_RECEIVE_FINISHED = 0xAA;

    /// <summary>
    /// Unity's Start method, called once on the frame when a script is enabled,
    /// just before any of the Update methods are called.
    /// Initializes the <see cref="SerialHandler"/>.
    /// </summary>
    private void Start()
    {
        serialHandler = new SerialHandler(portName, baudRate);

        serialHandler.ReadTimeout = readTimeout;   //setting the read timeout
        serialHandler.WriteTimeout = writeTimeout; //setting the write timeout
    }

    /// <summary>
    /// Unity's callback method invoked when the application or the editor is about to quit.
    /// Resets the device to a default state and closes the serial connection.
    /// </summary>
    private void OnApplicationQuit()
    {
        ResetDevice();
        serialHandler.Close();
    }

    //-------------------------------------------------------------------------------------------------------------//
    // Functions to send commands and get data from the ESP32
    //-------------------------------------------------------------------------------------------------------------//

    /// <summary>
    /// Sends the number of electrodes to the ESP32 and waits for a success response byte.
    /// </summary>
    /// <param name="electrodeNumber">The number of electrodes to configure on the device.</param>
    private void SendElectrodeNumber(int electrodeNumber)
    {
        serialHandler.Write(PC_ESP32_ELECTRODE_NUM);
        serialHandler.Write((byte)electrodeNumber);
    }

    /// <summary>
    /// Sends the stimulation polarity command to the ESP32 (1 = Anodic, 0 = Cathodic).
    /// </summary>
    /// <param name="polarity">The polarity value.</param>
    private void SendStimulationPolarity(int polarity)
    {
        serialHandler.Write(PC_ESP32_STIMULATION_POLARITY);
        serialHandler.Write((byte)polarity);
    }

    /// <summary>
    /// Sends the stimulation pulse height to the ESP32.
    /// </summary>
    /// <param name="pulseHeight">The desired pulse height.</param>
    private void SendStimulationPulseHeight(int pulseHeight)
    {
        serialHandler.Write(PC_ESP32_STIMULATION_PULSE_HEIGHT);
        serialHandler.Write((byte)pulseHeight);
    }

    /// <summary>
    /// Sends the stimulation pulse width to the ESP32.
    /// </summary>
    /// <param name="pulseWidth">The desired pulse width.</param>
    private void SendStimulationPulseWidth(int pulseWidth)
    {
        serialHandler.Write(PC_ESP32_STIMULATION_PULSE_WIDTH);
        serialHandler.Write((byte)pulseWidth);
    }

    /// <summary>
    /// Sends the sense pulse height to the ESP32.
    /// This is used for sensing the voltage of the electrodes.
    /// </summary>
    /// <param name="pulse_height">The sense pulse height.</param>
    private void SendSensePulseHeight(int pulse_height)
    {
        serialHandler.Write(PC_ESP32_SENSE_PULSE_HEIGHT);
        serialHandler.Write((byte)pulse_height);
    }

    /// <summary>
    /// Sends the sense pulse width to the ESP32.
    /// This width determines the duration of the sensing pulse for measuring electrode voltages.
    /// </summary>
    /// <param name="pulse_width">The sense pulse width.</param>
    private void SendSensePulseWidth(int pulse_width)
    {
        serialHandler.Write(PC_ESP32_SENSE_PULSE_WIDTH);
        serialHandler.Write((byte)pulse_width);
    }

    /// <summary>
    /// Sends the channel discharge time to the ESP32.
    /// This defines how long each channel will discharge after stimulation before the next pulse.
    /// </summary>
    /// <param name="discharge_time">The discharge time in device-specific units.</param>
    private void SendChannelDischargeTime(int discharge_time)
    {
        serialHandler.Write(PC_ESP32_CHANNEL_DISCHARGE_TIME);
        serialHandler.Write((byte)discharge_time);
    }

    /// <summary>
    /// Sends the stimulation frequency to the ESP32.
    /// </summary>
    /// <param name="stim_freq">The desired stimulation frequency.</param>
    private void SendStimulationFrequency(int stim_freq)
    {
        serialHandler.Write(PC_ESP32_STIMULATION_FREQUENCY);
        serialHandler.Write((byte)stim_freq);
    }

    /// <summary>
    /// Sends the stimulation pattern to the ESP32.
    /// The array length must match the current <see cref="NumberOfElectrodes"/>.
    /// </summary>
    /// <param name="stimPattern">
    /// An array representing the per-electrode values for the stimulation pattern.
    /// </param>
    private void SendStimulationPattern(int[] stimPattern)
    {
        if (stimPattern.Length != numberOfElectrodes)
        {
            Debug.LogError("Stimulation pattern length should be equal to the number of electrodes");
        }

        // Arrange the stimulation pattern in the correct order
        int[] stimPatternReordered = new int[numberOfElectrodes];
        for (int i = 0; i < numberOfElectrodes; i++)
        {
            stimPatternReordered[electrodeMapping[i]] = stimPattern[i];
        }

        serialHandler.Write(PC_ESP32_STIM_PATTERN);
        for (int i = 0; i < numberOfElectrodes; i++)
        {
            serialHandler.Write((byte)stimPatternReordered[i]);
        }
    }

    /// <summary>
    /// Requests the count of HV513 chips from the ESP32 and updates <see cref="hv513Number"/>.
    /// Temporarily adjusts the read timeout to allow the device to respond.
    /// </summary>
    private void UpdateAndGetHV513Count()
    {
        serialHandler.Write(PC_ESP32_HV513_NUM_REQUEST);
        serialHandler.ReadTimeout = 10;          // Increase the read timeout to 10ms because the HV513 number needs to be calculated and sent back
        hv513Number = serialHandler.Read();
        serialHandler.ReadTimeout = readTimeout; // Reset the read timeout
        Debug.Log("HV513 count: " + hv513Number);
    }

    /// <summary>
    /// Requests voltage readings from the ESP32 for all configured electrodes 
    /// and stores them in <see cref="voltages"/>.
    /// </summary>
    private void GetVoltageReadings()
    {
        /* Get voltage data from ESP32
           The ESP32 will send the voltage data of the electrodes to the PC */
        serialHandler.Write(PC_ESP32_MEASURE_REQUEST);
        int [] tempVoltages = new int[numberOfElectrodes];

        for (int i = 0; i < numberOfElectrodes; i++)
        {
            tempVoltages[i] = serialHandler.Read();
        }

        // mapping the voltage data to the correct order
        voltages = new int[numberOfElectrodes];
        for (int i = 0; i < numberOfElectrodes; i++)
        {
            voltages[i] = tempVoltages[electrodeMapping[i]];
        }
        Debug.Log("Voltage readings: " + string.Join(", ", voltages));
    }

    //-------------------------------------------------------------------------------------------------------------//
    // General Functions
    //-------------------------------------------------------------------------------------------------------------//

    /// <summary>
    /// Resets critical device parameters (e.g., pulse height/width, discharge time, etc.) to zero
    /// and updates the device accordingly.
    /// </summary>
    private void ResetDevice()
    {
        StimulationPulseHeight = 0;
        StimulationPulseWidth = 0;
        SensePulseHeight = 0;
        SensePulseWidth = 0;
        ChannelDischargeTime = 0;
        NumberOfElectrodes = 0;
    }

    //-------------------------------------------------------------------------------------------------------------//
    // Safety checking to check whether the changes done are safe or not
    //-------------------------------------------------------------------------------------------------------------//
    /// <summary>
    /// Performs a basic parameter check to ensure the configured settings are valid for operation.
    /// Logs errors if any required parameter is not set or if the electrode count exceeds device capacity.
    /// </summary>
    /// <returns>
    /// <c>true</c> if all parameters are within safe limits; otherwise <c>false</c>.
    /// </returns>
    public bool CheckSafety()
    {
        /* Check the safety of the parameters set for the application
           The function will check whether the parameters set are safe or not */
        if (numberOfElectrodes == 0)
        {
            Debug.LogError("Number of electrodes is not set");
            return false;
        }
        if (stimulationPulseHeight == 0)
        {
            Debug.LogError("Stimulation pulse height is not set");
            return false;
        }
        if (stimulationPulseWidth == 0)
        {
            Debug.LogError("Stimulation pulse width is not set");
            return false;
        }
        if (sensePulseHeight == 0)
        {
            Debug.LogError("Sense pulse height is not set");
            return false;
        }
        if (sensePulseWidth == 0)
        {
            Debug.LogError("Sense pulse width is not set");
            return false;
        }
        if (channelDischargeTime == 0)
        {
            Debug.LogError("Channel discharge time is not set");
            return false;
        }
        if (stimulationFrequency == 0)
        {
            Debug.LogError("Stimulation frequency is not set");
            return false;
        }
        if (hv513Number == 0)
        {
            Debug.LogError("HV513 count is not set");
            return false;
        }
        if (hv513Number * 8 < numberOfElectrodes)
        {
            Debug.LogError("Number of electrodes exceeds the number of outputs connected.\nPlease check the number of stacked switching modules");
            return false;
        }
        return true;
    }
}