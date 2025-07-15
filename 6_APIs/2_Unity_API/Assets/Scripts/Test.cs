using UnityEngine;
using System.Collections;
using System.Collections.Generic;

public class Test : MonoBehaviour
{
    public ETactileKit etactileKit; // Reference to the ETactileKit

    private PatternReader reader;

    void Start()
    {
        reader = new PatternReader();

        // Example path. Adjust depending on where you place your JSON file.
        string jsonPath = System.IO.Path.Combine(Application.streamingAssetsPath, "test_pattern.json");
        reader.LoadFile(jsonPath);

        StartCoroutine(ReadWrite());
    }

    void SetUpeTactileKit()
    {
        // Initilizing the ETactileKit in the correct order is important
        // 1. Set the number of electrodes
        etactileKit.NumberOfElectrodes = 8;
        // 2. Set the mapping function for the electrodes
        etactileKit.ElectrodeMapping = new int[] { 0, 1, 2, 3, 4, 5, 6, 7 };
        // 3. Set the stimulation parameters
        etactileKit.StimulationPulseHeight = 80;
        etactileKit.StimulationPulseWidth = 50;
        etactileKit.SensePulseHeight = 0;
        etactileKit.SensePulseWidth = 0;
        etactileKit.ChannelDischargeTime = 50;
        etactileKit.StimulationFrequency = 75;
        Debug.Log(etactileKit.Hv513Number);
    }
    IEnumerator ReadWrite()
    {
        yield return new WaitForSeconds(1f); // Wait for 1 second before starting the coroutine to initialize communication
        Debug.Log("Started Coroutine");

        // Setting up eTactileKit
        SetUpeTactileKit();

        int[] off_pattern = new int[8];
        for (int i = 0; i < 8; i++)
        {
            //on_pattern[i] = 1;
            off_pattern[i] = 0;
        }

        while (true)
        {
            // Get the first pattern
            Dictionary<string, object> patternData = reader.NextPattern();
            //Debug.Log("Pattern array: " + string.Join(",", (List<int>)patternData["pattern"]));
            //Debug.Log("ON time: " + patternData["on_time"]);
            //Debug.Log("OFF time: " + patternData["off_time"]);
            //Debug.Log("Frequency: " + patternData["frequency"]);
            //Debug.Log("Stim Mode: " + patternData["stim_mode"]);

            // Extract the pattern data
            var pattern = (List<int>)patternData["pattern"];
            // Convert List<int> to int[]
            int[] patternArray = new int[pattern.Count];
            for (int i = 0; i < pattern.Count; i++)
            {
                patternArray[i] = pattern[i];
            }

            float onTime = (int)patternData["on_time"] / 1000f;   // Convert milliseconds to seconds
            float offTime = (int)patternData["off_time"] / 1000f; // Convert milliseconds to seconds
            int frequency = (int)patternData["frequency"];
            int stimMode = (int)patternData["stim_mode"];

            // Set the stimulation parameters
            etactileKit.Polarity = stimMode;
            etactileKit.StimulationPattern = patternArray;
            yield return new WaitForSeconds(onTime);
            etactileKit.StimulationPattern = off_pattern;
            yield return new WaitForSeconds(offTime);

            //Debug.Log(etactileKit.Voltages);
            //yield return new WaitForSeconds(1f);
        }
    }
}