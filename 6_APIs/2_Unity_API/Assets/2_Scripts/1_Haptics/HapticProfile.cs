using UnityEngine;

/// <summary>
/// Reusable configuration asset describing the haptic response of an object. Create one via
/// <c>Create &gt; eTactileKit &gt; Haptic Profile</c> and assign it to a
/// <see cref="HapticProfileProvider"/> on the touchable object.
/// </summary>
[CreateAssetMenu(fileName = "HapticProfile", menuName = "eTactileKit/Haptic Profile")]
public class HapticProfile : ScriptableObject
{
    [Tooltip("Master switch - when off, this object never triggers stimulation.")]
    public bool enableHaptics = true;

    [Tooltip("Pattern played while a probe is penetrating this object.")]
    public PatternId patternId = PatternId.HorizontalScan;

    [Tooltip("Penetration depth (meters) a probe must reach before the pattern plays.")]
    [Min(0f)] public float minPenetrationDepthMeters = 0.002f;
}
