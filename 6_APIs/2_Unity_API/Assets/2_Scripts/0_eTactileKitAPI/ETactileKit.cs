using System;
using Debug = UnityEngine.Debug;

/// <summary>
/// Low-level driver for the eTactileKit ESP32 hardware. This is a faithful C# port of the
/// reference Python API (5_APIs/1_Python_API/api/etactilekit.py) and speaks the exact same
/// byte protocol.
///
/// Communication model:
///   * Global parameters (electrode count, stim mode, polarity, pulse width, sense pulse,
///     channel discharge time, frequency) are configured ONCE during setup.
///   * A stimulation "frame" is a single <see cref="SendStimPattern"/> call carrying one
///     little-endian uint16 intensity (0-4095, 12-bit DAC) per electrode. There is no
///     hardware concept of a frame count - temporal patterns are produced by sending
///     successive patterns over time from the Unity layer.
///   * The electrode mapping remaps application electrode indices to hardware channels:
///     hardwareChannel[mapping[i]] = intensity[applicationElectrode i].
/// </summary>
public class ETactileKit
{
    // Maximum intensity the 12-bit DAC can represent.
    public const int MaxIntensity = 4095;

    // PC -> ESP32 command opcodes (see api/etactilekit.py).
    private const byte PC_ESP32_MEASURE_REQUEST        = 0xFF; // request voltage readings
    private const byte PC_ESP32_STIM_PATTERN           = 0xFE; // stimulation pattern, n x uint16 LE
    private const byte PC_ESP32_STIMULATION_POLARITY   = 0xFD; // 1 byte
    private const byte PC_ESP32_ELECTRODE_NUM          = 0xFC; // 1 byte
    private const byte PC_ESP32_STIMULATION_MODE       = 0xFB; // 1 byte
    private const byte PC_ESP32_STIMULATION_PULSE_WIDTH = 0xFA; // uint16 LE (us)
    private const byte PC_ESP32_SENSE_PULSE_HEIGHT     = 0xF9; // 1 byte
    private const byte PC_ESP32_SENSE_PULSE_WIDTH      = 0xF8; // 1 byte
    private const byte PC_ESP32_CHANNEL_DISCHARGE_TIME = 0xF7; // 1 byte (us)
    private const byte PC_ESP32_STIMULATION_FREQUENCY  = 0xF6; // uint16 LE (Hz)
    private const byte PC_ESP32_HV513_NUM_REQUEST      = 0xF5; // request HV513 module count
    private const byte PC_ESP32_SYNC_CHECK             = 0xF4; // read back configured electrode number

    private ICommHandler commHandler;

    private int numberOfElectrodes;
    private int[] electrodeMapping;

    // Pre-built stimulation packet reused across sends to avoid per-frame allocation.
    private byte[] stimPacket;

    private int[] voltages = Array.Empty<int>();

    public bool IsConnected => commHandler != null && commHandler.IsOpen;
    public int NumberOfElectrodes => numberOfElectrodes;
    public int[] Voltages => voltages;

    //--------------------------------------------------------------------------------------//
    // Connection lifecycle
    //--------------------------------------------------------------------------------------//
    public void ConnectSerial(string portName, int baudRate, int readTimeoutMs, int writeTimeoutMs)
    {
#if UNITY_STANDALONE_WIN || UNITY_EDITOR
        commHandler = new SerialHandler(portName, baudRate)
        {
            ReadTimeout = readTimeoutMs,
            WriteTimeout = writeTimeoutMs
        };
#else
        Debug.LogError("[eTactileKit] Serial is not supported on this platform - use WiFi.");
#endif
    }

    public void ConnectWiFi(string ipAddress, int port, int readTimeoutMs, int writeTimeoutMs)
    {
        commHandler = new WiFiHandler(ipAddress, port)
        {
            ReadTimeout = readTimeoutMs,
            WriteTimeout = writeTimeoutMs
        };
    }

    public void Disconnect()
    {
        if (commHandler != null)
        {
            commHandler.Close();
            commHandler = null;
        }
    }

    //--------------------------------------------------------------------------------------//
    // Mapping (must be set before sending patterns)
    //--------------------------------------------------------------------------------------//
    /// <summary>
    /// Define the application-electrode -> hardware-channel mapping. Index i is the application
    /// electrode; <paramref name="mapping"/>[i] is the hardware channel that electrode drives.
    /// Also (re)allocates the reusable stimulation packet buffer.
    /// </summary>
    public void SetElectrodeMapping(int[] mapping)
    {
        if (mapping == null || mapping.Length == 0)
        {
            Debug.LogError("[eTactileKit] SetElectrodeMapping called with an empty mapping.");
            return;
        }

        electrodeMapping = (int[])mapping.Clone();
        numberOfElectrodes = electrodeMapping.Length;
        stimPacket = new byte[1 + numberOfElectrodes * 2];
        stimPacket[0] = PC_ESP32_STIM_PATTERN;
    }

    //--------------------------------------------------------------------------------------//
    // One-time setup parameters
    //--------------------------------------------------------------------------------------//
    public void SendElectrodeNumber(int electrodeNumber)
        => Write(new[] { PC_ESP32_ELECTRODE_NUM, (byte)electrodeNumber });

    public void SendStimulationMode(StimulationMode mode)
        => Write(new[] { PC_ESP32_STIMULATION_MODE, (byte)mode });

    public void SendStimulationPolarity(StimulationPolarity polarity)
        => Write(new[] { PC_ESP32_STIMULATION_POLARITY, (byte)polarity });

    public void SendStimulationPulseWidth(int pulseWidthUs)
        => Write(new[] { PC_ESP32_STIMULATION_PULSE_WIDTH, Low(pulseWidthUs), High(pulseWidthUs) });

    public void SendSensePulseHeight(int pulseHeight)
        => Write(new[] { PC_ESP32_SENSE_PULSE_HEIGHT, (byte)pulseHeight });

    public void SendSensePulseWidth(int pulseWidth)
        => Write(new[] { PC_ESP32_SENSE_PULSE_WIDTH, (byte)pulseWidth });

    public void SendChannelDischargeTime(int dischargeTimeUs)
        => Write(new[] { PC_ESP32_CHANNEL_DISCHARGE_TIME, (byte)dischargeTimeUs });

    public void SendStimulationFrequency(int frequencyHz)
        => Write(new[] { PC_ESP32_STIMULATION_FREQUENCY, Low(frequencyHz), High(frequencyHz) });

    //--------------------------------------------------------------------------------------//
    // Stimulation
    //--------------------------------------------------------------------------------------//
    /// <summary>
    /// Send one stimulation frame. <paramref name="intensities"/> holds one value per application
    /// electrode (in electrode-id order). Values are clamped to [0, 4095], remapped to hardware
    /// channels, packed little-endian and written in a single packet.
    /// </summary>
    public void SendStimPattern(int[] intensities)
    {
        if (!IsConnected)
        {
            return;
        }
        if (electrodeMapping == null || stimPacket == null)
        {
            Debug.LogError("[eTactileKit] SendStimPattern called before SetElectrodeMapping.");
            return;
        }
        if (intensities == null || intensities.Length != numberOfElectrodes)
        {
            Debug.LogError($"[eTactileKit] Stimulation pattern length must equal electrode count " +
                           $"({numberOfElectrodes}). Received: {(intensities?.Length ?? 0)}");
            return;
        }

        // Clear the payload region so any hardware channel not covered by the mapping stays at 0.
        Array.Clear(stimPacket, 1, stimPacket.Length - 1);

        for (int ch = 0; ch < numberOfElectrodes; ch++)
        {
            int value = intensities[ch];
            if (value < 0) value = 0;
            else if (value > MaxIntensity) value = MaxIntensity;

            int byteIndex = 1 + electrodeMapping[ch] * 2;
            stimPacket[byteIndex] = (byte)(value & 0xFF);
            stimPacket[byteIndex + 1] = (byte)((value >> 8) & 0xFF);
        }

        commHandler.Write(stimPacket);
    }

    //--------------------------------------------------------------------------------------//
    // Measurement / verification
    //--------------------------------------------------------------------------------------//
    /// <summary>Request voltage readings for all electrodes (application-electrode order).</summary>
    public int[] GetVoltageReadings(int timeoutMs)
    {
        if (!IsConnected || numberOfElectrodes == 0)
        {
            return null;
        }

        commHandler.ClearInputBuffer();
        Write(new[] { PC_ESP32_MEASURE_REQUEST });

        byte[] raw = commHandler.Read(numberOfElectrodes * 2, timeoutMs);
        if (raw == null || raw.Length != numberOfElectrodes * 2)
        {
            Debug.LogWarning($"[eTactileKit] Voltage read expected {numberOfElectrodes * 2} bytes, " +
                             $"got {(raw?.Length ?? 0)}");
            return null;
        }

        int[] hardware = new int[numberOfElectrodes];
        for (int i = 0; i < numberOfElectrodes; i++)
        {
            hardware[i] = raw[i * 2] | (raw[i * 2 + 1] << 8);
        }

        // Reverse the mapping so the caller gets values in application-electrode order.
        voltages = new int[numberOfElectrodes];
        for (int i = 0; i < numberOfElectrodes; i++)
        {
            voltages[i] = hardware[electrodeMapping[i]];
        }
        return voltages;
    }

    /// <summary>
    /// Query the number of HV513 driver chips. 1 means only the main controller; each switching
    /// module adds 8. Returns 0 on timeout.
    /// </summary>
    public int UpdateAndGetHv513Count(int timeoutMs)
    {
        if (!IsConnected)
        {
            return 0;
        }

        commHandler.ClearInputBuffer();
        Write(new[] { PC_ESP32_HV513_NUM_REQUEST });
        byte[] raw = commHandler.Read(1, timeoutMs);
        return raw != null && raw.Length == 1 ? raw[0] : 0;
    }

    /// <summary>Read back the configured electrode number to verify setup. Returns -1 on timeout.</summary>
    public int SyncCheck(int timeoutMs)
    {
        if (!IsConnected)
        {
            return -1;
        }

        commHandler.ClearInputBuffer();
        Write(new[] { PC_ESP32_SYNC_CHECK });
        byte[] raw = commHandler.Read(1, timeoutMs);
        return raw != null && raw.Length == 1 ? raw[0] : -1;
    }

    //--------------------------------------------------------------------------------------//
    // Helpers
    //--------------------------------------------------------------------------------------//
    private void Write(byte[] data)
    {
        if (IsConnected)
        {
            commHandler.Write(data);
        }
    }

    private static byte Low(int value) => (byte)(value & 0xFF);
    private static byte High(int value) => (byte)((value >> 8) & 0xFF);
}
