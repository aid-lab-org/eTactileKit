using UnityEngine;

/// <summary>
/// Attach to a touchable object (or its root) and assign a <see cref="HapticProfile"/>. A
/// <see cref="HapticController"/> resolves the provider from whichever collider a probe penetrates,
/// so a single provider on the root covers all of an object's child colliders.
/// </summary>
public class HapticProfileProvider : MonoBehaviour
{
    [Tooltip("The haptic response used when a probe penetrates this object.")]
    public HapticProfile profile;

    /// <summary>Find the provider governing a collider (searches the collider's parents).</summary>
    public static HapticProfileProvider Resolve(Collider collider)
        => collider != null ? collider.GetComponentInParent<HapticProfileProvider>() : null;
}
