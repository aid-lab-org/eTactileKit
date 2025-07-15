import processing.data.JSONArray;
import processing.data.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

class LoadData {
  
  PShape           obj_shape; // 3D model
  JSONObject       json_array_data;
  JSONArray        coordinates, electrodes;
  float            electrodeRadius;
  
  int     electrodes_number;
  int[]   mapping_func;

  void load2D(String array_pattern) {
    try {
      json_array_data      = loadJSONObject(array_pattern);
      coordinates          = json_array_data.getJSONArray("outline");
      electrodes           = json_array_data.getJSONArray("electrodes");
      electrodeRadius      = json_array_data.getFloat("electrode_radius") * 2;
      electrodes_number    = electrodes.size();
      
      // Sort electrodes by number
      //sortElectrodesByNumber();

      JSONArray mapping_array = json_array_data.getJSONArray("Mapping_func");
      mapping_func = new int[mapping_array.size()];
      for (int i = 0; i < mapping_array.size(); i++) {
        mapping_func[i] =  mapping_array.getInt(i);
      }
      
    } catch (Exception e) {
      println("Error loading JSON data: " + e);
      //Electrodes_number = 0;
      
    }
  }
  
  void load3D(String array_pattern, String object3D) {
    try {
      obj_shape = loadShape(object3D);
      json_array_data = loadJSONObject(array_pattern);
      //coordinates = json_array_Data.getJSONArray("outline");
      electrodes = json_array_data.getJSONArray("electrodes");
      electrodeRadius      = json_array_data.getFloat("electrode_radius");
      electrodes_number = electrodes.size();
      
      // Sort electrodes by number
      //sortElectrodesByNumber();

      JSONArray mapping_array = json_array_data.getJSONArray("Mapping_func");
      mapping_func = new int[mapping_array.size()];
      for (int i = 0; i < mapping_array.size(); i++) {
        mapping_func[i] = mapping_array.getInt(i);
      }
      
    } catch (Exception e) {
      println("Error loading JSON data: " + e);
      //Electrodes_number = 0;
      
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

  int getElectrodesNumber() {
    return electrodes_number;
  }
  
}
