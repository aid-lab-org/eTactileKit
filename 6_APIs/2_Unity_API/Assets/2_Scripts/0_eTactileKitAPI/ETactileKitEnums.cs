// Shared enumerations for the eTactileKit low-level API.
// These mirror the definitions in the reference Python API (api/etactilekit.py).

/// <summary>Stimulation waveform shape sent to the ESP32.</summary>
public enum StimulationMode
{
    Monophasic = 0,     // Single-phase pulse
    Biphasic = 1,       // Charge-balanced biphasic pulse
    ImpedanceOnly = 2   // Impedance measurement only (no stimulation)
}

/// <summary>Leading phase polarity of the stimulation pulse.</summary>
public enum StimulationPolarity
{
    Cathodic = 0,   // Cathodic-first (conventional for most neural stimulation)
    Anodic = 1      // Anodic-first
}

/// <summary>Transport used to reach the eTactileKit ESP32.</summary>
public enum ConnectionType
{
    Serial,
    WiFi
}
