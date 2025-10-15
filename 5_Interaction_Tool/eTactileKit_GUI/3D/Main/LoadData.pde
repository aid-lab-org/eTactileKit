/*ETactileKit - Visualization and Execution programme

LoadData :- used to load data from JSON files

Functions:  load()
*/

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;

class LoadData {
  
  PShape objShape;
  
  private JSONObject  json_pattern_data;
  private JSONObject  json_array_data;
  
  private JSONArray   patterns;
  private boolean     simulation;
  private boolean     execution;
  
  private JSONArray   electrodes;
  private int         electrodes_number;
  private float       electrodeRadius;
  private int[]       mapping_func;



  public void load3DObjArray(String array_file, String object3D) {
    try {
      json_array_data      = loadJSONObject(array_file);
      //coordinates          = json_array_data.getJSONArray("outline");
      electrodes           = json_array_data.getJSONArray("electrodes");
      electrodeRadius      = json_array_data.getFloat("electrode_radius");
      
      electrodes_number    = electrodes.size();
      on_board = false;
      
      // Check if "board" exists and equals "on_board"
      if (json_array_data.hasKey("board")) {
        String boardType = json_array_data.getString("board");
        if (boardType.equals("on_board")) {
          electrodes_number = 32;
          on_board = true;
        }
      }
      
    
      // Load Mapping_func array from the JSON file
      JSONArray mapping_array = json_array_data.getJSONArray("Mapping_func");
      
      mapping_func = new int[mapping_array.size()];
      for (int i = 0; i < mapping_array.size(); i++) {
        mapping_func[i] = (byte) mapping_array.getInt(i);
      }   
      
      if (object3D.toLowerCase().endsWith(".obj")) {
        objShape = loadShape(object3D);
        println("Loaded successfully: " + object3D);
      } else {
          valid_obj = false;
          println("Error: The file is not a .obj file.");
      }
      
    } catch (Exception e) {
      valid_files_array = false;
      println("Error loading JSON data: " + e);
      electrodes_number = 0;
    }
  }
  
  public void load3DPattern(String pattern_file) {
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
  
  //void getDimensions(PShape shape) {
  //  float minX = Float.MAX_VALUE, minY = Float.MAX_VALUE, minZ = Float.MAX_VALUE;
  //  float maxX = Float.MIN_VALUE, maxY = Float.MIN_VALUE, maxZ = Float.MIN_VALUE;
    
  //  for (int i = 0; i < shape.getChildCount(); i++) {  // Check all child shapes
  //    PShape child = shape.getChild(i);
  //    if (child == null) continue;
      
  //    for (int j = 0; j < child.getVertexCount(); j++) {
  //      PVector v = child.getVertex(j);
  //      minX = min(minX, v.x);
  //      minY = min(minY, v.y);
  //      minZ = min(minZ, v.z);
  //      maxX = max(maxX, v.x);
  //      maxY = max(maxY, v.y);
  //      maxZ = max(maxZ, v.z);
  //    }
  //  }
  
  //  float obj_width = maxX - minX;
  //  float obj_height = maxY - minY;
  //  float obj_depth = maxZ - minZ;
  
  //  println("Bounding Box Dimensions:");
  //  println("Width: " + obj_width);
  //  println("Height: " + obj_height);
  //  println("Depth: " + obj_depth);
  //}
}
