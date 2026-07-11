using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Drives the eTactileKit from collider penetration. Each frame it finds the deepest penetration
/// between any probe collider (any collider on <see cref="probeLayer"/>) and the touchable objects on
/// <see cref="interactableLayer"/>, resolves that object's <see cref="HapticProfile"/> through its
/// <see cref="HapticProfileProvider"/>, and - while the probe is deep enough - plays the profile's
/// pattern through the <see cref="ETactileKitManager"/>.
///
/// Playback is tied to the contacted collider: the pattern only restarts when a different object is
/// touched (or a genuine re-entry after leaving). While the same collider stays in contact and meets
/// the depth criterion the pattern continues from where it is - it is never replayed from the start.
/// A brief loss of contact (physics jitter, depth chatter at the threshold) within
/// <see cref="reacquireGraceSeconds"/> resumes at the current frame rather than restarting.
///
/// Probes and touchable objects are discovered by layer, so you never assign colliders here by hand:
/// put finger/tool colliders on the probe layer and touchable objects on the interactable layer.
/// </summary>
public class HapticController : MonoBehaviour
{
    [Header("Dependencies")]
    [SerializeField] private ETactileKitManager manager;

    [Header("Layers")]
    [Tooltip("Colliders on this layer act as probes (finger tips, tool tips). They are found " +
             "automatically - just put your probe colliders on this layer.")]
    [SerializeField] private LayerMask probeLayer;

    [Tooltip("Layer(s) holding the touchable objects.")]
    [SerializeField] private LayerMask interactableLayer = ~0;

    [Header("Playback")]
    [Tooltip("Grace period (seconds) for a momentary loss of contact. If the SAME collider is " +
             "re-acquired within this window the pattern resumes where it left off instead of " +
             "restarting. Set to 0 to restart on any loss of contact.")]
    [Min(0f)] [SerializeField] private float reacquireGraceSeconds = 0.2f;

    [Tooltip("Log start / resume / stop transitions to the Console (for verification).")]
    [SerializeField] private bool logStateChanges = false;

    // Reused overlap query buffer to avoid per-frame allocation.
    private readonly Collider[] overlapBuffer = new Collider[16];

    // Probe colliders discovered from probeLayer.
    private readonly List<Collider> probes = new List<Collider>();
    private bool warnedProbeSetup;

    // --- Playback state ---
    private enum Phase { On, Off }
    private HapticPattern activePattern;
    private Collider currentContactCollider;   // the collider the current pattern is bound to
    private float lastContactTime;             // Time.time of the last active frame (for the grace window)
    private int frameIndex;
    private int direction = 1;
    private Phase phase = Phase.On;
    private float phaseTimerSeconds;
    private bool finishedOnce;   // Once-mode patterns idle here after the last frame
    private bool isPlaying;      // true while actively driving frames

    private void Update()
    {
        if (manager == null)
        {
            return;
        }

        Collider contact = ResolveDeepestContact(out float depth, out HapticProfile profile);
        bool active = contact != null
                      && profile.enableHaptics
                      && depth >= profile.minPenetrationDepthMeters;

        if (!active)
        {
            Suspend();
            return;
        }

        lastContactTime = Time.time;

        HapticPattern pattern = PatternDB.Get(profile.patternId, manager.ElectrodeCount);
        if (pattern == null || pattern.FrameCount == 0)
        {
            Suspend();
            return;
        }

        if (contact != currentContactCollider || pattern != activePattern)
        {
            // A different object - or a genuine re-entry after the grace window - starts over.
            currentContactCollider = contact;
            StartPattern(pattern);
            Log($"start '{pattern.name}' on '{contact.name}'");
        }
        else if (!isPlaying)
        {
            // Same collider re-acquired within the grace window: resume, do not restart.
            ResumePlayback();
            Log($"resume '{pattern.name}' on '{contact.name}' at frame {frameIndex}");
        }

        if (finishedOnce)
        {
            return; // Once pattern complete; stay silent until the probe leaves and re-enters
        }

        AdvancePlayback();
    }

    private void OnEnable() => RefreshProbes();

    private void OnDisable() => StopPlayback();

    /// <summary>
    /// Rescan the scene for probe colliders (all enabled colliders on <see cref="probeLayer"/>). Call
    /// this if probe colliders are spawned after the controller is enabled (e.g. late-instantiated
    /// VR hands).
    /// </summary>
    public void RefreshProbes()
    {
        probes.Clear();
        Collider[] all = FindObjectsByType<Collider>(FindObjectsSortMode.None);
        foreach (Collider c in all)
        {
            if ((probeLayer.value & (1 << c.gameObject.layer)) != 0)
            {
                probes.Add(c);
            }
        }

        if (probes.Count > 0)
        {
            warnedProbeSetup = false;
        }
        else if (!warnedProbeSetup)
        {
            warnedProbeSetup = true;
            if (probeLayer.value == 0)
            {
                Debug.LogWarning("[eTactileKit] HapticController 'Probe Layer' is set to Nothing. " +
                                 "Put your finger/tool tip colliders on a layer and select it in " +
                                 "'Probe Layer'.", this);
            }
            else
            {
                Debug.LogWarning("[eTactileKit] HapticController found no probe colliders on 'Probe " +
                                 "Layer'. Check that each finger/tool tip collider's GameObject Layer " +
                                 "matches the 'Probe Layer' selected on this controller.", this);
            }
        }
    }

    //--------------------------------------------------------------------------------------//
    // Penetration detection
    //--------------------------------------------------------------------------------------//
    /// <summary>
    /// Find the deepest-penetrated touchable collider across all probes, along with its depth and
    /// haptic profile. Returns null when nothing (with a profile) is penetrated.
    /// </summary>
    private Collider ResolveDeepestContact(out float deepestDepth, out HapticProfile profile)
    {
        deepestDepth = 0f;
        profile = null;
        Collider deepestCollider = null;

        // Probes may not exist yet on the first frames (e.g. VR hands still spawning); rescan until
        // at least one appears.
        if (probes.Count == 0)
        {
            RefreshProbes();
        }

        foreach (Collider probe in probes)
        {
            if (probe == null || !probe.enabled)
            {
                continue;
            }

            Bounds bounds = probe.bounds;
            int hitCount = Physics.OverlapBoxNonAlloc(
                bounds.center, bounds.extents, overlapBuffer, Quaternion.identity,
                interactableLayer, QueryTriggerInteraction.Collide);

            for (int i = 0; i < hitCount; i++)
            {
                Collider other = overlapBuffer[i];
                if (other == probe)
                {
                    continue;
                }

                bool overlapped = Physics.ComputePenetration(
                    probe, probe.transform.position, probe.transform.rotation,
                    other, other.transform.position, other.transform.rotation,
                    out _, out float distance);

                if (overlapped && distance > deepestDepth)
                {
                    HapticProfileProvider provider = HapticProfileProvider.Resolve(other);
                    if (provider != null && provider.profile != null)
                    {
                        deepestDepth = distance;
                        deepestCollider = other;
                        profile = provider.profile;
                    }
                }
            }
        }

        return deepestCollider;
    }

    //--------------------------------------------------------------------------------------//
    // Playback state machine
    //--------------------------------------------------------------------------------------//
    private void StartPattern(HapticPattern pattern)
    {
        activePattern = pattern;
        frameIndex = 0;
        direction = 1;
        finishedOnce = false;
        isPlaying = true;
        EnterFrameOn();
    }

    /// <summary>Same collider re-acquired within the grace window: keep the position, resume output.</summary>
    private void ResumePlayback()
    {
        isPlaying = true;
        if (!finishedOnce)
        {
            EnterFrameOn(); // re-assert the current frame (output was turned off while suspended)
        }
    }

    /// <summary>
    /// Contact/criterion lost. Stop stimulation immediately (safety), but keep the pattern position
    /// for <see cref="reacquireGraceSeconds"/> so a momentary loss resumes instead of restarting.
    /// </summary>
    private void Suspend()
    {
        if (isPlaying)
        {
            manager.SendOff();
            isPlaying = false;
            Log("suspend (contact/criteria lost)");
        }

        if (currentContactCollider != null &&
            Time.time - lastContactTime > reacquireGraceSeconds)
        {
            ForgetContact(); // grace elapsed: a later contact will start the pattern over
            Log("forget contact (grace elapsed)");
        }
    }

    /// <summary>Full stop and reset (used on disable).</summary>
    private void StopPlayback()
    {
        if (isPlaying)
        {
            manager.SendOff();
            isPlaying = false;
        }
        ForgetContact();
    }

    private void ForgetContact()
    {
        currentContactCollider = null;
        activePattern = null;
        finishedOnce = false;
        frameIndex = 0;
        direction = 1;
    }

    private void AdvancePlayback()
    {
        phaseTimerSeconds -= Time.deltaTime;
        if (phaseTimerSeconds > 0f)
        {
            return;
        }

        if (phase == Phase.On)
        {
            HapticFrame frame = activePattern.frames[frameIndex];
            if (frame.offTimeMs > 0f)
            {
                manager.SendOff();
                phase = Phase.Off;
                phaseTimerSeconds = frame.offTimeMs / 1000f;
                return;
            }
        }

        AdvanceFrame();
    }

    private void AdvanceFrame()
    {
        int count = activePattern.FrameCount;
        if (count <= 1)
        {
            if (activePattern.mode == PatternPlaybackMode.Once)
            {
                FinishOnce();
                return;
            }
            EnterFrameOn(); // single-frame Loop/Bounce: just replay it
            return;
        }

        switch (activePattern.mode)
        {
            case PatternPlaybackMode.Once:
                if (frameIndex >= count - 1)
                {
                    FinishOnce();
                    return;
                }
                frameIndex++;
                break;

            case PatternPlaybackMode.Loop:
                frameIndex = (frameIndex + 1) % count;
                break;

            case PatternPlaybackMode.Bounce:
                if (frameIndex + direction > count - 1) direction = -1;
                else if (frameIndex + direction < 0) direction = 1;
                frameIndex += direction;
                break;
        }

        EnterFrameOn();
    }

    private void EnterFrameOn()
    {
        HapticFrame frame = activePattern.frames[frameIndex];
        manager.SendFrame(frame.activeElectrodes);
        phase = Phase.On;
        phaseTimerSeconds = frame.onTimeMs / 1000f;
    }

    private void FinishOnce()
    {
        manager.SendOff();
        finishedOnce = true;
    }

    private void Log(string message)
    {
        if (logStateChanges)
        {
            Debug.Log($"[eTactileKit] HapticController: {message}", this);
        }
    }
}
