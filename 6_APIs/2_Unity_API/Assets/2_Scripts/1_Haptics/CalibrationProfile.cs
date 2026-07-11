using System;
using UnityEngine;

/// <summary>
/// In-memory representation of an eTactileKit calibration profile. The JSON layout matches the
/// files exported by the desktop calibration application, e.g.:
/// <code>
/// {
///   "format": "etactilekit_calibration_profile",
///   "version": "1.0",
///   "created_at": "2026-06-29T22:48:24",
///   "layout": { "name": "...", "slug": "...", "electrode_count": 32 },
///   "electrodes": [ { "id": 0, "label": "E0", "mapping": 0, "intensity": 300 }, ... ]
/// }
/// </code>
///
/// Calibration carries only two things per electrode: the hardware <c>mapping</c> and the
/// per-electrode <c>intensity</c> applied when that electrode is active in a pattern. All other
/// stimulation parameters (pulse width, frequency, mode, ...) are global and live on the manager.
/// </summary>
[Serializable]
public class CalibrationProfile
{
    public string format = "etactilekit_calibration_profile";
    public string version = "1.0";
    public string created_at;
    public CalibrationLayout layout = new CalibrationLayout();
    public CalibrationElectrode[] electrodes = Array.Empty<CalibrationElectrode>();

    public int ElectrodeCount => layout != null ? layout.electrode_count : 0;

    /// <summary>Application-electrode -> hardware-channel mapping array, indexed by electrode id.</summary>
    public int[] BuildMapping()
    {
        int count = ElectrodeCount;
        int[] mapping = new int[count];
        for (int i = 0; i < electrodes.Length && i < count; i++)
        {
            int id = electrodes[i].id;
            if (id >= 0 && id < count)
            {
                mapping[id] = electrodes[i].mapping;
            }
        }
        return mapping;
    }

    /// <summary>Per-electrode active intensity, indexed by electrode id.</summary>
    public int[] BuildIntensities()
    {
        int count = ElectrodeCount;
        int[] intensities = new int[count];
        for (int i = 0; i < electrodes.Length && i < count; i++)
        {
            int id = electrodes[i].id;
            if (id >= 0 && id < count)
            {
                intensities[id] = Mathf.Max(0, electrodes[i].intensity);
            }
        }
        return intensities;
    }

    public static CalibrationProfile FromJson(string json) => JsonUtility.FromJson<CalibrationProfile>(json);

    public string ToJson(bool prettyPrint = true)
    {
        created_at = DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss");
        return JsonUtility.ToJson(this, prettyPrint);
    }

    /// <summary>
    /// Validate structural integrity. Returns false with a reason when the profile is unusable
    /// (no electrodes, mismatched count, or a mapping that is not a permutation of 0..count-1).
    /// </summary>
    public bool Validate(out string error)
    {
        if (layout == null || ElectrodeCount <= 0)
        {
            error = "Profile has no layout / electrode_count.";
            return false;
        }
        if (electrodes == null || electrodes.Length != ElectrodeCount)
        {
            error = $"electrodes array length ({electrodes?.Length ?? 0}) does not match " +
                    $"electrode_count ({ElectrodeCount}).";
            return false;
        }

        int count = ElectrodeCount;
        bool[] mappingSeen = new bool[count];
        foreach (CalibrationElectrode e in electrodes)
        {
            if (e.id < 0 || e.id >= count)
            {
                error = $"Electrode id {e.id} is out of range [0, {count - 1}].";
                return false;
            }
            if (e.mapping < 0 || e.mapping >= count)
            {
                error = $"Electrode {e.id} mapping {e.mapping} is out of range [0, {count - 1}].";
                return false;
            }
            if (mappingSeen[e.mapping])
            {
                error = $"Duplicate hardware mapping {e.mapping}; mapping must be a permutation.";
                return false;
            }
            mappingSeen[e.mapping] = true;
        }

        error = null;
        return true;
    }
}

[Serializable]
public class CalibrationLayout
{
    public string name;
    public string slug;
    public int electrode_count;
}

[Serializable]
public class CalibrationElectrode
{
    public int id;
    public string label;
    public int mapping;
    public int intensity;
}
