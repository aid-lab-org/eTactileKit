@FunctionalInterface
interface ShapeChecker3D {
  boolean isInsideShape3D(float x, float y, float z);
}

import peasy.*;
import java.util.Arrays;

public class ETactile {
  ShapeChecker3D shapeChecker;
  
  LoadData dataLoader;
  SaveToJson saveJson;
  Visualizer visualizer;
  PeasyCam cam;
  
  int[] elecs_data;
  int[] prev_elecs_Data;
  int electrodes_number;
  float electrodeSize;
  float electrodeRadius;
  int[]   mapping_func;
  
  float scaleFactor;
  boolean needToScale = false;
  
  PShape  obj_shape; // 3D model
  
  JSONArray outer_array = new JSONArray();
  JSONArray coordinates, electrodes;
  int delay_time;
  int frequency = 75;
  int stimMode = 1; // 1-Anodic, 0-Cathodic
  int pattern_red, pattern_green, pattern_blue;
  int pattern_type = 0;
  boolean blink_state = true;
  int[] electrode_to_activate;
  
  boolean simulation = true;
  boolean execution = true;
  
  String output_name;
  
  int iteration = 0;
  boolean started_writing = false;
  
  boolean display;
  boolean saved = false;
  
  PApplet parent; 
  
  public ETactile(PApplet parent) {
    this.parent = parent;
    parent.registerMethod("pre", this);
    parent.registerMethod("draw", this);
    
    shapeChecker = this::defaultIsInsideShape3D;
  }
  
    public void pre(){
      eTactile.setBackground(0);     
    }
  
  public void draw() {
    if (g.is3D()){
      eTactile.create_pattern_3D();
    }
    else{
      eTactile.create_pattern_2D();
    }
  }
 
  void create_pattern_2D() {

    visualizer.visualizeArrayPattern();
    
    iteration += 1;
    
    if (!Arrays.equals(elecs_data, prev_elecs_Data)) {
      
      if (!started_writing){
   
        iteration = 0;
        
        started_writing = true;
        
        System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
         
      }
      
      else{
        
        int delay_time_n = iteration * delay_time;
      
        saveJson.saveDataToJson(outer_array, delay_time_n, prev_elecs_Data, frequency, stimMode);
        
        System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
        
        iteration = 0;
      }
      
    }
    delay(eTactile.delay_time);
  }
  
  
  void create_pattern_3D() {
   
    visualizer.visualize3DObject();
    visualizer.visualizeArrayPattern3D();
    
    iteration += 1;
  
    if (!Arrays.equals(elecs_data, prev_elecs_Data)) {
      //delay_time = pattern3D.getDelaytime();
      
      if (!started_writing){
        
        iteration = 0;
        
        started_writing = true;
        
        System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
        
      }
      
      else{
        
        int delay_time_n = iteration * delay_time;
      
        saveJson.saveDataToJson(outer_array, delay_time_n, prev_elecs_Data, frequency, stimMode);
        
        System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
        
        iteration = 0;
      }
    }
    delay(eTactile.delay_time);
  }
  
  int getDelayTime(){
    return delay_time;
  }
  
  void eTframedelay(int delay){
    delay_time = delay;
  }
  
  void eTfreq(int freq){
    frequency = freq;
  }
  
  void eTmode(String Mode){
    if (Mode.equals("Cathodic") || Mode.equals("cathodic") || Mode.equals("C") || Mode.equals("c")){
      stimMode = 0;
    }
    else if (Mode.equals("Anodic") || Mode.equals("anodic") || Mode.equals("A") || Mode.equals("a")){
      stimMode = 1;
    } 
    else{
      println("Invalid argument for stimulation mode -> Stimulation mode setted to Anodic");
    }
  }
  
  void eTstrokeColour(int red, int green, int blue){
    pattern_red = red;
    pattern_green = green;
    pattern_blue = blue;
    stroke(red, green, blue);
  }
  
  void setBackground(int bgColour){
    background(bgColour);
    if(g.is3D()){
      visualizer.visualize3DObject();
      noStroke();         // No outline for the plane
    }
    else{
    visualizer.visualizeBoardShape();
    }
  }
  
  void setBlinkState(boolean blinkState){
    blink_state = blinkState;
  }
  
  void toggleBlinkState(){
    blink_state = !blink_state;
  }
  
  void activateElectrodes(int[] electrodes){
    electrode_to_activate = electrodes;
  }
  
  boolean isInsideShape2D(float x, float y, int i) {
    if (pattern_type == 0){
      for (float j = x - electrodeSize/100; j <= x + electrodeSize/100; j++){
        for (float k = y - electrodeSize/100; k <= y + electrodeSize/100; k++){
           color c = get(int(j), int(k));  // Get color at (110, 110)
           if (int(red(c)) != 150 && int(green(c)) != 150 && int(blue(c)) != 150){
             return true;
           }
        }
      }
      return false;
    }
    else if (pattern_type == 1){
      // Check if the electrode overlaps with any of the ellipses
      if (blink_state){
        return true;
      }else{
      return false;
      }
    }
    else if (pattern_type == 2){
      // Check if i exists in the electrode_to_activate array
      for (int electrode : electrode_to_activate) {
          if (electrode == i && blink_state) {
              return true; // i is inside the array
              
          }
        }
      return false; // i is not inside the array
      }
    else{
      return false;
    }
  }
  
  void patternType(String type){
    if (type == "G"){
      pattern_type = 0;
    }
    else if (type == "B"){
      pattern_type = 1;
    }
    else if (type == "S"){
      pattern_type = 2;
    }
  }
  
 void terminate(){
   if (!saved){
     save_pattern();
     println("Pattern created and saved to JSON file.");
     saved = true;
   }
 }
  
  void save_pattern(){
    saveJson.saveJSONfile(outer_array);
  }
  
  void setup2D(String array_pattern, String output_file){
    dataLoader = new LoadData();
    saveJson = new SaveToJson();
    
    dataLoader.load2D(array_pattern);
    
    
    electrodes_number = dataLoader.electrodes_number;
    elecs_data = new int[electrodes_number];
    
    //pattern2D = createPattern("display");
    
    eTactile.setupEnv();
    
    display = true;
    visualizer.visualizeBoardShape();
    visualizer.visualizeArrayPattern();
    display = false;
    
    output_name = output_file;
    
  }
  
  void setup3D(String electrodes_locs, String object3D, String output_file){
    
    dataLoader = new LoadData();
    saveJson = new SaveToJson();
    
    // Initialize PeasyCam for interactive 3D navigation
    cam = new PeasyCam(parent, 500);
    cam.setMinimumDistance(100);
    cam.setMaximumDistance(2000);
    
    dataLoader.load3D(electrodes_locs, object3D);
    
    electrodes_number = dataLoader.electrodes_number;
    elecs_data = new int[electrodes_number];
    
    
    eTactile.setupEnv();
    obj_shape = dataLoader.obj_shape; // 3D model
    
    display = true;
    visualizer.visualize3DObject();
    visualizer.visualizeArrayPattern3D();
    display = false;
    
    
     lights(); // Enable lighting for better 3D visualization
     
     output_name = output_file;
  }
  
  void setupEnv(){
    // Retrieve and store electrode data from the loaded JSON
    electrodes_number = dataLoader.electrodes_number;
    coordinates = dataLoader.coordinates;
    electrodes = dataLoader.electrodes;
    electrodeRadius = dataLoader.electrodeRadius;
    mapping_func = dataLoader.mapping_func;
    println("Number of Electrodes: " + electrodes_number);
    
    // Initialize an array to store previous electrode data
    prev_elecs_Data = new int[electrodes_number];
    
    visualizer = new Visualizer();
    
    // Prepare JSON objects for data storage
    saveJson.json = new JSONObject();
    outer_array = new JSONArray();
    
    background(0);  // Set the background color to black
    
    //eTactile = new ETactile(this);
    
    noStroke();
  }
  
  void setIsInsideShape3D(ShapeChecker3D checker){
    shapeChecker = checker != null ? checker : this::defaultIsInsideShape3D;
  }
  
  boolean defaultIsInsideShape3D(float x, float y, float z){
    return false;
  }
  
  boolean isInsideShape3D(float x, float y, float z){
    return shapeChecker.isInsideShape3D(x, y, z);
  }
}
