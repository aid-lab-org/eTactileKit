using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Custom inspector for <see cref="ETactileKitManager"/>. Draws the standard connection / global
/// parameter fields, then a calibration section that imports/exports the desktop-app JSON format and
/// lets you tune the per-electrode intensity (and hardware mapping) directly.
/// </summary>
[CustomEditor(typeof(ETactileKitManager))]
public class ETactileKitManagerEditor : Editor
{
    private SerializedProperty activeProfileProp;
    private bool showElectrodes = true;

    private void OnEnable()
    {
        activeProfileProp = serializedObject.FindProperty("activeProfile");
    }

    public override void OnInspectorGUI()
    {
        serializedObject.Update();

        // Everything except the calibration profile (drawn with a custom section below).
        DrawPropertiesExcluding(serializedObject, "m_Script", "activeProfile");

        EditorGUILayout.Space(10f);
        DrawCalibrationSection();

        serializedObject.ApplyModifiedProperties();
    }

    private void DrawCalibrationSection()
    {
        EditorGUILayout.LabelField("Calibration Profile", EditorStyles.boldLabel);

        EditorGUILayout.BeginHorizontal();
        bool import = GUILayout.Button("Import JSON", GUILayout.MinHeight(24f));
        bool export = GUILayout.Button("Export JSON", GUILayout.MinHeight(24f));
        EditorGUILayout.EndHorizontal();

        if (import) { ImportCalibrationJson(); GUIUtility.ExitGUI(); }
        if (export) { ExportCalibrationJson(); GUIUtility.ExitGUI(); }

        SerializedProperty layoutProp = activeProfileProp.FindPropertyRelative("layout");
        SerializedProperty electrodesProp = activeProfileProp.FindPropertyRelative("electrodes");

        if (layoutProp != null)
        {
            EditorGUILayout.PropertyField(layoutProp.FindPropertyRelative("name"), new GUIContent("Layout Name"));
            EditorGUILayout.PropertyField(layoutProp.FindPropertyRelative("electrode_count"), new GUIContent("Electrode Count"));
        }

        if (electrodesProp == null || !electrodesProp.isArray)
        {
            EditorGUILayout.HelpBox("No electrodes - import a calibration profile JSON.", MessageType.Info);
            return;
        }

        showElectrodes = EditorGUILayout.Foldout(showElectrodes, $"Electrodes ({electrodesProp.arraySize})", true);
        if (!showElectrodes)
        {
            return;
        }

        EditorGUILayout.BeginVertical(EditorStyles.helpBox);
        EditorGUILayout.BeginHorizontal();
        EditorGUILayout.LabelField("Electrode", GUILayout.Width(90f));
        EditorGUILayout.LabelField("Mapping", GUILayout.Width(90f));
        EditorGUILayout.LabelField("Intensity");
        EditorGUILayout.EndHorizontal();

        for (int i = 0; i < electrodesProp.arraySize; i++)
        {
            SerializedProperty e = electrodesProp.GetArrayElementAtIndex(i);
            SerializedProperty label = e.FindPropertyRelative("label");
            SerializedProperty mapping = e.FindPropertyRelative("mapping");
            SerializedProperty intensity = e.FindPropertyRelative("intensity");

            EditorGUILayout.BeginHorizontal();
            EditorGUILayout.LabelField(string.IsNullOrEmpty(label.stringValue) ? $"E{i}" : label.stringValue, GUILayout.Width(90f));
            mapping.intValue = Mathf.Max(0, EditorGUILayout.IntField(mapping.intValue, GUILayout.Width(90f)));
            intensity.intValue = Mathf.Clamp(EditorGUILayout.IntField(intensity.intValue), 0, ETactileKit.MaxIntensity);
            EditorGUILayout.EndHorizontal();
        }
        EditorGUILayout.EndVertical();
    }

    private void ImportCalibrationJson()
    {
        string path = EditorUtility.OpenFilePanel("Import Calibration JSON", Application.dataPath, "json");
        if (string.IsNullOrEmpty(path))
        {
            return;
        }

        string json;
        try
        {
            json = File.ReadAllText(path);
        }
        catch (IOException ex)
        {
            EditorUtility.DisplayDialog("Import Calibration JSON", $"Failed to read file:\n{ex.Message}", "OK");
            return;
        }

        CalibrationProfile profile = CalibrationProfile.FromJson(json);
        string error = "could not parse JSON";
        if (profile == null || !profile.Validate(out error))
        {
            EditorUtility.DisplayDialog("Import Calibration JSON",
                $"Invalid calibration profile:\n{error}", "OK");
            return;
        }

        ETactileKitManager manager = (ETactileKitManager)target;
        Undo.RecordObject(manager, "Import Calibration JSON");
        manager.ApplyImportedProfile(profile);
        EditorUtility.SetDirty(manager);
        PrefabUtility.RecordPrefabInstancePropertyModifications(manager);
        serializedObject.Update();
        EditorUtility.DisplayDialog("Import Calibration JSON", $"Imported calibration from:\n{path}", "OK");
    }

    private void ExportCalibrationJson()
    {
        string path = EditorUtility.SaveFilePanel(
            "Export Calibration JSON", Application.dataPath, "etactilekit_calibration", "json");
        if (string.IsNullOrEmpty(path))
        {
            return;
        }

        ETactileKitManager manager = (ETactileKitManager)target;
        string json = manager.ActiveProfile.ToJson(true);

        try
        {
            File.WriteAllText(path, json);
        }
        catch (IOException ex)
        {
            EditorUtility.DisplayDialog("Export Calibration JSON", $"Failed to write file:\n{ex.Message}", "OK");
            return;
        }

        EditorUtility.DisplayDialog("Export Calibration JSON", $"Exported calibration to:\n{path}", "OK");
    }
}
