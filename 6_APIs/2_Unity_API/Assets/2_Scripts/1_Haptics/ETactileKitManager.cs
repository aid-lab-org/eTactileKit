using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

/// <summary>
/// Scene-level owner of the eTactileKit hardware. Holds the connection settings, the global
/// stimulation parameters (set once at setup) and the active calibration profile, and exposes a
/// simple <see cref="SendFrame"/> entry point that the haptics layer uses to drive the hardware.
///
/// Calibration supplies the per-electrode hardware mapping and the per-electrode active intensity,
/// and also defines the electrode count - nothing here hard-codes it. A "frame" is the set of
/// electrode ids that are ON; when sent, those electrodes are driven at their calibrated intensity
/// (all others = 0), the array is remapped to hardware channels by <see cref="ETactileKit"/>, and
/// transmitted in one packet.
///
/// <see cref="AmplitudeGain"/> is a global multiplier applied to every calibrated intensity at send
/// time (1 = as calibrated). The scaled value is rounded to the nearest integer and clamped to the
/// hardware's 12-bit DAC range, so the per-electrode balance from calibration is preserved while the
/// overall strength can be adjusted in one place - live, without reconnecting.
/// </summary>
public class ETactileKitManager : MonoBehaviour
{
    /// <summary>Bounds of the global amplitude gain slider.</summary>
    public const float MinAmplitudeGain = 0f;
    public const float MaxAmplitudeGain = 1.5f;

    [Header("Connection")]
    [SerializeField] private ConnectionType connectionType = ConnectionType.Serial;
    [SerializeField] private string portName = "COM12";
    [SerializeField] private int baudRate = 921600;
    [Tooltip("WiFi: manual board IP. Used when Use Discovery is off, or as a fallback when no " +
             "kit answers discovery (e.g. AP mode is always 192.168.4.1).")]
    [SerializeField] private string ipAddress = "192.168.4.1";
    [SerializeField] private int wifiPort = 8080;
    [SerializeField] private int readTimeoutMs = 20;
    [SerializeField] private int writeTimeoutMs = 20;

    [Header("WiFi Discovery (STA mode / multiple kits)")]
    [Tooltip("Find the board automatically by UDP broadcast instead of a hard-coded IP. " +
             "Recommended when kits share one router. Unity cannot resolve mDNS (.local), so " +
             "this is how a specific kit is located in station mode.")]
    [SerializeField] private bool useDiscovery = false;
    [Tooltip("Connect to the kit with this unique 6-hex ID (on its label, the Console log, or " +
             "'python -m api.discovery'). Leave blank to use the only/first kit found.")]
    [SerializeField] private string targetDeviceId = "";
    [Tooltip("How long to wait for kits to answer discovery, in milliseconds.")]
    [SerializeField] private int discoveryTimeoutMs = 1000;

    [Header("Global Stimulation Parameters (set once at setup)")]
    [SerializeField] private StimulationMode stimulationMode = StimulationMode.Monophasic;
    [SerializeField] private StimulationPolarity polarity = StimulationPolarity.Anodic;
    [Tooltip("Stimulation pulse width in microseconds.")]
    [SerializeField] private int pulseWidthUs = 100;
    [Tooltip("Stimulation frequency in Hz.")]
    [SerializeField] private int frequencyHz = 50;
    [Tooltip("Channel discharge time in microseconds.")]
    [SerializeField] private int channelDischargeTimeUs = 50;
    [Tooltip("Sense pulse height used for impedance measurement (0 disables sensing).")]
    [SerializeField] private int sensePulseHeight = 0;
    [Tooltip("Sense pulse width used for impedance measurement (0 disables sensing).")]
    [SerializeField] private int sensePulseWidth = 0;

    [Header("Calibration")]
    [Tooltip("Default calibration file inside StreamingAssets, loaded on Start when no profile is " +
             "set in the inspector. Generate it with the eTactileKitExplorer desktop application.")]
    [SerializeField] private string defaultCalibrationFileName = "template_32_electrode_calibration.json";
    [SerializeField] private CalibrationProfile activeProfile = new CalibrationProfile();

    [Header("Amplitude")]
    [Tooltip("Global gain applied to every electrode's calibrated intensity before it is sent to the " +
             "hardware. 1 = use the calibration values as-is; below 1 attenuates, above 1 boosts. " +
             "Scaled values are rounded to the nearest integer and clamped to the 12-bit DAC range. " +
             "Takes effect immediately, including while playing.")]
    [Range(MinAmplitudeGain, MaxAmplitudeGain)]
    [SerializeField] private float amplitudeGain = 1f;

    [Header("Testing")]
    [Tooltip("Cycle all electrodes on/off after connecting, to verify the hardware link.")]
    [SerializeField] private bool runConnectionTest = false;

    private ETactileKit etk;
    private int[] cachedIntensities;    // per-electrode active intensity, indexed by electrode id
    private int[] frameIntensityBuffer; // reused scratch buffer for SendFrame / SendOff
    private bool isTesting;

    public bool IsConnected => etk != null && etk.IsConnected;
    public int ElectrodeCount => activeProfile != null ? activeProfile.ElectrodeCount : 0;
    public CalibrationProfile ActiveProfile => activeProfile;

    /// <summary>
    /// Global gain applied to every electrode's calibrated intensity before it is sent (1 = as
    /// calibrated). Clamped to [<see cref="MinAmplitudeGain"/>, <see cref="MaxAmplitudeGain"/>].
    /// Changing it takes effect on the next frame sent - no reconnect or re-setup needed.
    /// </summary>
    public float AmplitudeGain
    {
        get => amplitudeGain;
        set => amplitudeGain = Mathf.Clamp(value, MinAmplitudeGain, MaxAmplitudeGain);
    }

    private void Start() => StartCoroutine(StartupRoutine());

    private IEnumerator StartupRoutine()
    {
        yield return LoadDefaultCalibrationRoutine();
        ConnectDevice();

        if (runConnectionTest && IsConnected)
        {
            StartCoroutine(RunConnectionTest());
        }
    }

    private void OnApplicationQuit() => DisconnectDevice();
    private void OnDisable() => DisconnectDevice();

    //--------------------------------------------------------------------------------------//
    // Calibration
    //--------------------------------------------------------------------------------------//
    /// <summary>
    /// Load the default calibration file from StreamingAssets if the active profile is missing or
    /// invalid. On Android, StreamingAssets lives inside the compressed APK, so it is read with
    /// <see cref="UnityWebRequest"/>; on desktop it is read directly from disk. Generate the file
    /// with the eTactileKitExplorer desktop application.
    /// </summary>
    private IEnumerator LoadDefaultCalibrationRoutine()
    {
        if (activeProfile != null && activeProfile.Validate(out _))
        {
            yield break;
        }

        string path = Path.Combine(Application.streamingAssetsPath, defaultCalibrationFileName);

#if UNITY_ANDROID && !UNITY_EDITOR
        using (UnityWebRequest request = UnityWebRequest.Get(path))
        {
            yield return request.SendWebRequest();
            if (request.result == UnityWebRequest.Result.Success)
            {
                ApplyImportedProfile(CalibrationProfile.FromJson(request.downloadHandler.text));
            }
            else
            {
                Debug.LogError($"[eTactileKit] Could not read default calibration '{path}': {request.error}");
            }
        }
#else
        if (!File.Exists(path))
        {
            Debug.LogError($"[eTactileKit] Default calibration not found at '{path}'. Place a profile " +
                           "in StreamingAssets or import one in the inspector.");
            yield break;
        }

        try
        {
            ApplyImportedProfile(CalibrationProfile.FromJson(File.ReadAllText(path)));
        }
        catch (IOException ex)
        {
            Debug.LogError($"[eTactileKit] Failed to read default calibration '{path}': {ex.Message}");
        }
#endif
    }

    /// <summary>Replace the active profile (used by the inspector import and default loading).</summary>
    public void ApplyImportedProfile(CalibrationProfile profile)
    {
        if (profile == null)
        {
            Debug.LogError("[eTactileKit] Tried to apply a null calibration profile.");
            return;
        }
        if (!profile.Validate(out string error))
        {
            Debug.LogError($"[eTactileKit] Calibration profile rejected: {error}");
            return;
        }
        activeProfile = profile;
        if (IsConnected)
        {
            SetupDevice(); // re-apply mapping + intensities live
        }
    }

    //--------------------------------------------------------------------------------------//
    // Connection lifecycle
    //--------------------------------------------------------------------------------------//
    public void ConnectDevice()
    {
        if (IsConnected)
        {
            return;
        }
        string error = "No calibration profile assigned.";
        if (activeProfile == null || !activeProfile.Validate(out error))
        {
            Debug.LogError($"[eTactileKit] Cannot connect without a valid calibration profile. {error}");
            return;
        }

#if !UNITY_STANDALONE_WIN && !UNITY_EDITOR
        // Serial is a desktop-only transport; on the headset (and other non-Windows targets) the kit
        // is reached over WiFi. Force WiFi so a scene left on Serial still connects.
        if (connectionType == ConnectionType.Serial)
        {
            Debug.LogWarning("[eTactileKit] Serial is unavailable on this platform - using WiFi.");
            connectionType = ConnectionType.WiFi;
        }
#endif

        etk = new ETactileKit();
        if (connectionType == ConnectionType.Serial)
        {
            etk.ConnectSerial(portName, baudRate, readTimeoutMs, writeTimeoutMs);
        }
        else
        {
            string host = ResolveWiFiHost(out int resolvedPort);
            etk.ConnectWiFi(host, resolvedPort, readTimeoutMs, writeTimeoutMs);
        }

        if (!etk.IsConnected)
        {
            Debug.LogError("[eTactileKit] Connection failed - check the device and settings.");
            etk = null;
            return;
        }

        SetupDevice();
    }

    /// <summary>
    /// Choose the WiFi host to connect to. With discovery enabled, broadcast for kits and return
    /// the IP of the one matching <see cref="targetDeviceId"/> (or the first found); otherwise, or
    /// if nothing answers, fall back to the manually configured <see cref="ipAddress"/> (also the
    /// AP-mode address 192.168.4.1). Unity/.NET cannot resolve mDNS, so discovery is how a specific
    /// kit is located in station mode.
    /// </summary>
    private string ResolveWiFiHost(out int resolvedPort)
    {
        // Fallback host/port: the manual IP (also the AP-mode 192.168.4.1) on the configured port.
        resolvedPort = wifiPort;

        if (!useDiscovery)
        {
            return ipAddress;
        }

        List<ETactileKitDiscovery.DiscoveredDevice> devices =
            ETactileKitDiscovery.Discover(discoveryTimeoutMs);

        if (devices.Count == 0)
        {
            Debug.LogWarning($"[eTactileKit] No kits discovered; falling back to IP '{ipAddress}'.");
            return ipAddress;
        }

        ETactileKitDiscovery.DiscoveredDevice chosen;
        if (!string.IsNullOrEmpty(targetDeviceId))
        {
            chosen = devices.Find(d => string.Equals(d.id, targetDeviceId, StringComparison.OrdinalIgnoreCase));
            if (chosen == null)
            {
                Debug.LogError($"[eTactileKit] Kit '{targetDeviceId}' not found. Discovered: " +
                               $"{DeviceIds(devices)}. Falling back to IP '{ipAddress}'.");
                return ipAddress;
            }
        }
        else
        {
            chosen = devices[0];
            if (devices.Count > 1)
            {
                Debug.LogWarning($"[eTactileKit] {devices.Count} kits found ({DeviceIds(devices)}); " +
                                 $"using '{chosen.id}'. Set Target Device Id to pick one.");
            }
        }

        Debug.Log($"[eTactileKit] Discovered kit {chosen.id} at {chosen.ip}:{chosen.port} ({chosen.mode}).");
        resolvedPort = chosen.port;
        return chosen.ip;
    }

    private static string DeviceIds(List<ETactileKitDiscovery.DiscoveredDevice> devices)
        => string.Join(", ", devices.ConvertAll(d => d.id).ToArray());

    /// <summary>Run the one-time setup sequence (matches the reference Python setup order).</summary>
    private void SetupDevice()
    {
        if (!IsConnected)
        {
            return;
        }

        int[] mapping = activeProfile.BuildMapping();
        cachedIntensities = activeProfile.BuildIntensities();
        frameIntensityBuffer = new int[ElectrodeCount];

        etk.SetElectrodeMapping(mapping);
        etk.SendElectrodeNumber(ElectrodeCount);
        etk.SendStimulationMode(stimulationMode);
        etk.SendStimulationPolarity(polarity);
        etk.SendStimulationPulseWidth(pulseWidthUs);
        etk.SendSensePulseHeight(sensePulseHeight);
        etk.SendSensePulseWidth(sensePulseWidth);
        etk.SendChannelDischargeTime(channelDischargeTimeUs);
        etk.SendStimulationFrequency(frequencyHz);

        int hv513 = etk.UpdateAndGetHv513Count(500);
        int sync = etk.SyncCheck(200);
        Debug.Log($"[eTactileKit] Setup complete. Electrodes={ElectrodeCount}, HV513 modules={hv513}, " +
                  $"sync check returned electrode number={sync}.");
    }

    public void DisconnectDevice()
    {
        if (etk == null)
        {
            return;
        }
        isTesting = false;
        SendOff();
        etk.Disconnect();
        etk = null;
    }

    //--------------------------------------------------------------------------------------//
    // Stimulation
    //--------------------------------------------------------------------------------------//
    /// <summary>
    /// Calibrated intensity of one electrode scaled by <see cref="AmplitudeGain"/>, rounded to the
    /// nearest integer (the hardware takes integers only) and clamped to the 12-bit DAC range.
    /// </summary>
    private int ScaledIntensity(int electrodeId)
    {
        return Mathf.Clamp(
            Mathf.RoundToInt(cachedIntensities[electrodeId] * amplitudeGain),
            0, ETactileKit.MaxIntensity);
    }

    /// <summary>
    /// Send a single frame. <paramref name="activeElectrodeIds"/> lists the electrode ids that are ON
    /// this frame; each is driven at its calibrated intensity scaled by <see cref="AmplitudeGain"/>,
    /// and all others are 0. Ids outside [0, ElectrodeCount) are ignored with a warning. Returns false
    /// if not connected or testing.
    /// </summary>
    public bool SendFrame(int[] activeElectrodeIds)
    {
        if (!IsConnected || isTesting || cachedIntensities == null || frameIntensityBuffer == null)
        {
            return false;
        }

        for (int i = 0; i < frameIntensityBuffer.Length; i++)
        {
            frameIntensityBuffer[i] = 0;
        }

        if (activeElectrodeIds != null)
        {
            foreach (int id in activeElectrodeIds)
            {
                if (id >= 0 && id < frameIntensityBuffer.Length)
                {
                    frameIntensityBuffer[id] = ScaledIntensity(id);
                }
                else
                {
                    Debug.LogWarning($"[eTactileKit] Electrode id {id} is out of range " +
                                     $"[0, {ElectrodeCount - 1}] and was ignored.");
                }
            }
        }

        etk.SendStimPattern(frameIntensityBuffer);
        return true;
    }

    /// <summary>Turn every electrode off.</summary>
    public void SendOff()
    {
        if (!IsConnected || frameIntensityBuffer == null)
        {
            return;
        }
        for (int i = 0; i < frameIntensityBuffer.Length; i++)
        {
            frameIntensityBuffer[i] = 0;
        }
        etk.SendStimPattern(frameIntensityBuffer);
    }

    //--------------------------------------------------------------------------------------//
    // Connection test
    //--------------------------------------------------------------------------------------//
    private IEnumerator RunConnectionTest()
    {
        isTesting = true;
        Debug.Log("[eTactileKit] Connection test running - all electrodes pulse on/off every 0.5s.");

        int[] allOn = new int[ElectrodeCount];
        int[] allOff = new int[ElectrodeCount];

        bool on = false;
        while (isTesting && IsConnected)
        {
            if (on)
            {
                // Rebuilt each cycle so the amplitude slider takes effect live during the test.
                for (int i = 0; i < ElectrodeCount; i++)
                {
                    allOn[i] = ScaledIntensity(i);
                }
            }

            etk.SendStimPattern(on ? allOn : allOff);
            on = !on;
            yield return new WaitForSeconds(0.5f);
        }

        isTesting = false;
    }
}
