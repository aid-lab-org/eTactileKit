using System;

/// <summary>How a multi-frame pattern advances while it is being played.</summary>
public enum PatternPlaybackMode
{
    Once,   // play the frame sequence one time, then idle until re-triggered
    Loop,   // play frames 0..N-1 then restart at 0, repeating while active
    Bounce  // play frames forward then backward (ping-pong) while active
}

/// <summary>Identifies a pattern in <see cref="PatternDB"/>. Add new ids here.</summary>
public enum PatternId
{
    None,
    HorizontalScan,
    VerticalScan,
    Blink,
    Buzz
}

/// <summary>
/// One step of a tactile pattern. <see cref="activeElectrodes"/> lists the electrode ids that are ON
/// (value 1) for this frame; every other electrode is off. On-electrodes are replaced by their
/// calibrated intensity when sent. The frame is held for <see cref="onTimeMs"/>, then all electrodes
/// are turned off for <see cref="offTimeMs"/> before the next frame.
///
/// Listing active electrode ids (rather than a full 0/1 array) keeps patterns independent of the
/// electrode count, which is defined by the loaded calibration profile - not hard-coded here.
/// </summary>
[Serializable]
public class HapticFrame
{
    public int[] activeElectrodes;
    public float onTimeMs;
    public float offTimeMs;

    public HapticFrame(int[] activeElectrodes, float onTimeMs, float offTimeMs)
    {
        this.activeElectrodes = activeElectrodes;
        this.onTimeMs = onTimeMs;
        this.offTimeMs = offTimeMs;
    }
}

/// <summary>A named tactile pattern: an ordered set of frames plus a playback mode.</summary>
[Serializable]
public class HapticPattern
{
    public string name;
    public PatternPlaybackMode mode;
    public HapticFrame[] frames;

    public int FrameCount => frames != null ? frames.Length : 0;

    public HapticPattern(string name, PatternPlaybackMode mode, HapticFrame[] frames)
    {
        this.name = name;
        this.mode = mode;
        this.frames = frames;
    }
}

/// <summary>
/// Code-defined library of tactile patterns.
///
/// A pattern is a list of frames; each frame lists the electrode ids that are ON, plus an on-time
/// and off-time in milliseconds. To add a pattern:
///   1. add a value to <see cref="PatternId"/>,
///   2. build a <see cref="HapticPattern"/> below by listing the active electrode ids per frame,
///   3. return it from <see cref="Get"/>.
///
/// The example patterns below are authored for the default "Fingerpad TactDeform 32" layout: a 6x6
/// grid with the four corners removed (32 electrodes). Electrode ids are arranged as:
/// <code>
///          col0  col1  col2  col3  col4  col5
///   row0:    .     0     1     2     3     .
///   row1:    4     5     6     7     8     9
///   row2:   10    11    12    13    14    15
///   row3:   16    17    18    19    20    21
///   row4:   22    23    24    25    26    27
///   row5:    .    28    29    30    31     .
/// </code>
/// If your hardware numbers electrodes differently, adjust the ids in each frame to match.
///
/// Two authoring styles are shown:
///   * Manual - list the active ids per frame (<see cref="HorizontalScan"/>, <see cref="VerticalScan"/>).
///   * Programmatic - build frames with a loop from the active electrode count (<see cref="Blink"/>,
///     <see cref="Buzz"/>). These take the count so they work for any layout; the built pattern is
///     cached so the same instance is returned every frame.
/// </summary>
public static class PatternDB
{
    /// <summary>
    /// Resolve a pattern by id. <paramref name="electrodeCount"/> (from the active calibration) is
    /// used by the loop-generated patterns. Returns null for <see cref="PatternId.None"/>.
    /// </summary>
    public static HapticPattern Get(PatternId id, int electrodeCount)
    {
        switch (id)
        {
            case PatternId.HorizontalScan: return HorizontalScan;
            case PatternId.VerticalScan:   return VerticalScan;
            case PatternId.Blink:          return Blink(electrodeCount);
            case PatternId.Buzz:           return Buzz(electrodeCount);
            default:                       return null;
        }
    }

    // A vertical bar of electrodes sweeping left -> right across the grid (one column per frame).
    private static readonly HapticPattern HorizontalScan = new HapticPattern(
        "Horizontal Scan",
        PatternPlaybackMode.Loop,
        new[]
        {
            new HapticFrame(new[] { 4, 10, 16, 22 },        80f, 0f), // col 0 (left edge)
            new HapticFrame(new[] { 0, 5, 11, 17, 23, 28 }, 80f, 0f), // col 1
            new HapticFrame(new[] { 1, 6, 12, 18, 24, 29 }, 80f, 0f), // col 2
            new HapticFrame(new[] { 2, 7, 13, 19, 25, 30 }, 80f, 0f), // col 3
            new HapticFrame(new[] { 3, 8, 14, 20, 26, 31 }, 80f, 0f), // col 4
            new HapticFrame(new[] { 9, 15, 21, 27 },        80f, 0f), // col 5 (right edge)
        });

    // A horizontal bar of electrodes sweeping top -> bottom (one row per frame).
    private static readonly HapticPattern VerticalScan = new HapticPattern(
        "Vertical Scan",
        PatternPlaybackMode.Loop,
        new[]
        {
            new HapticFrame(new[] { 0, 1, 2, 3 },           80f, 0f), // row 0 (top edge)
            new HapticFrame(new[] { 4, 5, 6, 7, 8, 9 },     80f, 0f), // row 1
            new HapticFrame(new[] { 10, 11, 12, 13, 14, 15 }, 80f, 0f), // row 2
            new HapticFrame(new[] { 16, 17, 18, 19, 20, 21 }, 80f, 0f), // row 3
            new HapticFrame(new[] { 22, 23, 24, 25, 26, 27 }, 80f, 0f), // row 4
            new HapticFrame(new[] { 28, 29, 30, 31 },       80f, 0f), // row 5 (bottom edge)
        });

    //--------------------------------------------------------------------------------------//
    // Programmatic (loop-built) patterns. These are generated from the active electrode count
    // and cached, so the same instance is returned on every call while the count is unchanged.
    //--------------------------------------------------------------------------------------//

    private static HapticPattern blinkCache;
    private static int blinkCacheCount = -1;

    // Blink: every electrode on together for 200 ms, off for 200 ms, repeating.
    private static HapticPattern Blink(int electrodeCount)
    {
        if (electrodeCount <= 0)
        {
            return null;
        }
        if (blinkCache == null || blinkCacheCount != electrodeCount)
        {
            int[] all = new int[electrodeCount];
            for (int i = 0; i < electrodeCount; i++)
            {
                all[i] = i; // activate every electrode id
            }
            blinkCache = new HapticPattern(
                "Blink", PatternPlaybackMode.Loop,
                new[] { new HapticFrame(all, 200f, 200f) });
            blinkCacheCount = electrodeCount;
        }
        return blinkCache;
    }

    private static HapticPattern buzzCache;
    private static int buzzCacheCount = -1;

    // Buzz: activate one electrode per frame with no gap, scanning through them all rapidly.
    private static HapticPattern Buzz(int electrodeCount)
    {
        if (electrodeCount <= 0)
        {
            return null;
        }
        if (buzzCache == null || buzzCacheCount != electrodeCount)
        {
            HapticFrame[] frames = new HapticFrame[electrodeCount];
            for (int i = 0; i < electrodeCount; i++)
            {
                frames[i] = new HapticFrame(new[] { i }, 40f, 0f);
            }
            buzzCache = new HapticPattern("Buzz", PatternPlaybackMode.Loop, frames);
            buzzCacheCount = electrodeCount;
        }
        return buzzCache;
    }
}
