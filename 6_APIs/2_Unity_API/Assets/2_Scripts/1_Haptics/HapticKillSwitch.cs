using UnityEngine;

/// <summary>
/// Unified emergency stop for the eTactileKit, used on **both** PC / Quest Link and the Quest 3
/// standalone build. Because interactions are hands-first and the headset has no keyboard, the kill
/// switch is a deliberate, uncommon hand gesture: pinch <b>middle + ring + pinky</b> to the thumb at
/// once (index left free) on either hand and hold for <see cref="holdSeconds"/>. When triggered it
/// calls <see cref="ETactileKitManager.DisconnectDevice"/>, which sends OFF and drops the connection.
///
/// Uses only the manager's public API plus Meta XR <c>OVRHand</c>, so the core manager stays free of
/// any XR-SDK dependency. Requires the Meta XR SDK and hand tracking enabled.
/// </summary>
public class HapticKillSwitch : MonoBehaviour
{
    [SerializeField] private ETactileKitManager manager;

    [Tooltip("Hand anchors' OVRHand components. Assign whichever hands you use (either may be left empty).")]
    [SerializeField] private OVRHand leftHand;
    [SerializeField] private OVRHand rightHand;

    [Tooltip("How long the gesture must be held before the kill switch fires.")]
    [Min(0f)] [SerializeField] private float holdSeconds = 1f;

    private float heldFor;

    private void Update()
    {
        if (manager == null)
        {
            return;
        }

        bool gesture = IsKillGesture(leftHand) || IsKillGesture(rightHand);
        heldFor = gesture ? heldFor + Time.deltaTime : 0f;

        if (heldFor >= holdSeconds && gesture)
        {
            heldFor = 0f;
            Debug.LogWarning("[eTactileKit] Kill gesture held - stopping stimulation and disconnecting.");
            manager.DisconnectDevice();
        }
    }

    /// <summary>
    /// The deliberate stop pose: middle, ring and pinky pinched to the thumb while the index stays
    /// free (so a normal index-thumb "select" pinch never triggers it).
    /// </summary>
    private static bool IsKillGesture(OVRHand hand)
    {
        if (hand == null || !hand.IsTracked)
        {
            return false;
        }

        return hand.GetFingerIsPinching(OVRHand.HandFinger.Middle)
            && hand.GetFingerIsPinching(OVRHand.HandFinger.Ring)
            && hand.GetFingerIsPinching(OVRHand.HandFinger.Pinky)
            && !hand.GetFingerIsPinching(OVRHand.HandFinger.Index);
    }
}
