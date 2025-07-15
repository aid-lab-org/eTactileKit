using System;
using System.IO;
using System.Collections.Generic;
using Newtonsoft.Json;
using UnityEngine;

/// <summary>
/// A class for reading and iterating through pattern data from a JSON file.
/// This class ignores any Execution/Simulation flags and only uses "Pattern_Data".
/// </summary>
public class PatternReader
{
    /// <summary>
    /// Holds all pattern groups loaded from the JSON's "Pattern_Data" key.
    /// Each element is a list containing one or more pattern dictionaries.
    /// </summary>
    private List<List<Dictionary<string, object>>> patterns;

    /// <summary>
    /// An index pointing to the current pattern group (used in <see cref="NextPattern"/>).
    /// </summary>
    private int index;

    /// <summary>
    /// Initializes a new instance of the <see cref="PatternReader"/> class.
    /// Sets up empty structures for pattern storage.
    /// </summary>
    public PatternReader()
    {
        patterns = new List<List<Dictionary<string, object>>>();
        index = 0;
    }

    /// <summary>
    /// Loads the JSON file located at the given path and extracts "Pattern_Data".
    /// The "Execution" and "Simulation" sections (if present) are ignored.
    /// </summary>
    /// <param name="filePath">The path to the JSON file. This must contain a top-level "Pattern_Data" key.</param>
    /// <exception cref="FileNotFoundException">Thrown if the file does not exist at the provided path.</exception>
    /// <exception cref="JsonException">Thrown if JSON parsing fails or "Pattern_Data" is not found.</exception>
    public void LoadFile(string filePath)
    {
        if (!File.Exists(filePath))
        {
            throw new FileNotFoundException($"Could not find JSON file at: {filePath}");
        }

        try
        {
            // Read entire JSON file into a string
            string jsonContent = File.ReadAllText(filePath);

            // Parse the JSON into a Dictionary
            var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(jsonContent);

            // Verify that "Pattern_Data" exists
            if (!data.ContainsKey("Pattern_Data"))
            {
                throw new JsonException("JSON is missing the required 'Pattern_Data' key.");
            }

            // Convert the "Pattern_Data" object into a JArray for easier iteration
            var jArrayPatternData = data["Pattern_Data"] as Newtonsoft.Json.Linq.JArray;
            if (jArrayPatternData == null)
            {
                throw new JsonException("'Pattern_Data' is not a valid JSON array.");
            }

            // Clear out any existing patterns
            patterns.Clear();

            // For each element in Pattern_Data (which itself is an array of arrays), 
            // parse a list of pattern dictionaries.
            foreach (var item in jArrayPatternData)
            {
                // Each top-level item is expected to be an array of dictionaries
                var patternGroupJArray = item as Newtonsoft.Json.Linq.JArray;
                if (patternGroupJArray == null)
                {
                    Debug.LogWarning("Encountered a 'pattern group' that is not a valid array. Skipping...");
                    continue;
                }

                // Build one "pattern group"
                var patternGroup = new List<Dictionary<string, object>>();
                foreach (var dictItem in patternGroupJArray)
                {
                    // Convert each array element into a Dictionary<string, object>
                    var dict = JsonConvert.DeserializeObject<Dictionary<string, object>>(dictItem.ToString());
                    patternGroup.Add(dict);
                }

                patterns.Add(patternGroup);
            }

            // Reset index so iteration starts at the first pattern
            index = 0;
        }
        catch (JsonException ex)
        {
            Debug.LogError($"JSON parsing error: {ex.Message}");
            throw;
        }
        catch (Exception ex)
        {
            Debug.LogError($"Unexpected error loading JSON file: {ex.Message}");
            throw;
        }
    }

    /// <summary>
    /// Resets the internal pattern index to the start (0),
    /// so that the next call to <see cref="NextPattern"/> will return the first pattern.
    /// </summary>
    public void ResetPatternIndex()
    {
        index = 0;
    }

    /// <summary>
    /// Fetches the next pattern in a cyclic manner from the loaded "Pattern_Data".
    /// Once the last pattern group is reached, the index wraps back to 0.
    /// </summary>
    /// <returns>
    /// A dictionary with the following keys:
    /// - "pattern"   (List&lt;int&gt;): An array of integers representing the pattern.
    /// - "on_time"   (int)            : The ON delay.
    /// - "off_time"  (int)            : The OFF delay.
    /// - "frequency" (int)            : The frequency parameter.
    /// - "stim_mode" (int)            : The stimulation mode (e.g. 0 for Cathodic, 1 for Anodic).
    /// </returns>
    /// <exception cref="InvalidOperationException">
    /// Thrown if no pattern data is loaded or the current pattern group is empty.
    /// </exception>
    public Dictionary<string, object> NextPattern()
    {
        if (patterns == null || patterns.Count == 0)
        {
            throw new InvalidOperationException("Pattern data has not been loaded or is empty.");
        }

        // Retrieve the current pattern group
        var patternGroup = patterns[index];
        if (patternGroup.Count == 0)
        {
            throw new InvalidOperationException($"Pattern group at index {index} is empty.");
        }

        // The Python code always takes the first dictionary in the group (patternGroup[0]).
        var patternInfo = patternGroup[0];

        // Move to the next pattern group, wrapping around with modulo
        index = (index + 1) % patterns.Count;

        // Build a result dictionary
        var result = new Dictionary<string, object>();

        // Extract the "pattern" array
        // The JSON structure shows "pattern" is an array of 8 integers (e.g., [0,1,0,1, ...]).
        if (patternInfo.TryGetValue("pattern", out object patternObj))
        {
            // Convert patternObj to a list of integers
            var patternJArray = patternObj as Newtonsoft.Json.Linq.JArray;
            if (patternJArray != null)
            {
                List<int> patternVals = new List<int>();
                foreach (var val in patternJArray)
                {
                    patternVals.Add((int)val);
                }
                result["pattern"] = patternVals;
            }
            else
            {
                // If for some reason it's not an array, store an empty list
                result["pattern"] = new List<int>();
            }
        }
        else
        {
            result["pattern"] = new List<int>();
        }

        // Extract delay -> "on_time" and "off_time"
        // The JSON structure for "delay" is something like: {"ON":200,"OFF":0}
        if (patternInfo.TryGetValue("delay", out object delayObj))
        {
            var delayDict = delayObj as Newtonsoft.Json.Linq.JObject;
            if (delayDict != null)
            {
                // ON time
                if (delayDict["ON"] != null)
                {
                    result["on_time"] = (int)delayDict["ON"];
                }
                else
                {
                    result["on_time"] = 0;
                }

                // OFF time
                if (delayDict["OFF"] != null)
                {
                    result["off_time"] = (int)delayDict["OFF"];
                }
                else
                {
                    result["off_time"] = 0;
                }
            }
        }
        else
        {
            result["on_time"] = 0;
            result["off_time"] = 0;
        }

        // Extract params -> "frequency" and "stim_mode"
        if (patternInfo.TryGetValue("params", out object paramsObj))
        {
            var paramsDict = paramsObj as Newtonsoft.Json.Linq.JObject;
            if (paramsDict != null)
            {
                if (paramsDict["frequency"] != null)
                {
                    result["frequency"] = (int)paramsDict["frequency"];
                }
                else
                {
                    result["frequency"] = 0;
                }

                if (paramsDict["stim_mode"] != null)
                {
                    result["stim_mode"] = (int)paramsDict["stim_mode"];
                }
                else
                {
                    result["stim_mode"] = 1;
                }
            }
        }
        else
        {
            result["frequency"] = 0;
            result["stim_mode"] = 1;
        }

        return result;
    }
}
