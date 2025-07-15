/*ETactileKit - Visualization and Execution programme

LoadData :- used to load data from JSON files

Functions:  load()
*/

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

class LoadData {
  private JSONObject  json_pattern_data;
  private JSONObject  json_array_data;
  
  private JSONArray   patterns;
  private boolean     simulation;
  private boolean     execution = true;
  
  private JSONArray   coordinates, electrodes;
  private int         electrodes_number;
  private float       electrodeRadius;
  private int[]       mapping_func;



  public void loadArray(String array_file) {
    try {
      json_array_data      = loadJSONObject(array_file);
      coordinates          = json_array_data.getJSONArray("outline");
      electrodes           = json_array_data.getJSONArray("electrodes");
      electrodeRadius      = json_array_data.getFloat("electrode_radius") * 2;
      electrodes_number    = electrodes.size();
      
      //sortElectrodesByNumber();
    
      // Load Mapping_func array from the JSON file
      JSONArray mapping_array = json_array_data.getJSONArray("Mapping_func");
      
      mapping_func = new int[mapping_array.size()];
      for (int i = 0; i < mapping_array.size(); i++) {
        mapping_func[i] = mapping_array.getInt(i);
      }   
    } catch (Exception e) {
      valid_files_array = false;
      println("Error loading JSON data: " + e);
      electrodes_number = 0;
    }
  }
  
  public void loadPattern(String pattern_file) {
    try {
      json_pattern_data    = loadJSONObject(pattern_file);
      patterns             = json_pattern_data.getJSONArray("Pattern_Data");
      simulation           = json_pattern_data.getBoolean("Simulation");
      execution            = json_pattern_data.getBoolean("Execution");
      
      general_check = true;
     
      if (patterns.getJSONArray(0).getJSONObject(0).getJSONArray("pattern").size() != electrodes_number && patterns.getJSONArray(patterns.size()).getJSONObject(0).getJSONArray("pattern").size() != electrodes_number ){
        println("Electrode number missmatch!");
      }
    
    } catch (Exception e) {
      valid_files_pattern = false;
      println("Error loading JSON data: " + e);
      simulation        = false;
      execution         = false;
      patterns          = null;
      
      if (!general_check){
        uiManager.showPatternFileErrorDialog();
      }
      else{
        uiManager.showElectrodeMissMatchErrorDialog();
        general_check = false;
      }
    }
  }
  
    void sortElectrodesByNumber() {
    ArrayList<JSONObject> electrodes_list = new ArrayList<JSONObject>();
    
    // Convert JSONArray to ArrayList
    for (int i = 0; i < electrodes.size(); i++) {
      electrodes_list.add(electrodes.getJSONObject(i));
    }
    
    // Sort ArrayList based on the number field
    Collections.sort(electrodes_list, new Comparator<JSONObject>() {
      @Override
      public int compare(JSONObject o1, JSONObject o2) {
        return Integer.compare(o1.getInt("number"), o2.getInt("number"));
      }
    });
    
    // Create a new JSONArray from the sorted list
    electrodes = new JSONArray();
    for (JSONObject electrode : electrodes_list) {
      electrodes.append(electrode);
    }
  }
}
