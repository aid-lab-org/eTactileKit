/*ETactileKit - Visualization and Execution programme

GraphicsManager :- used to give visual feedback to user

Functions:  setupGraphics()
            displayInstructions()
            resetElectrodes()
            drawElectrodes()
            visualizeAndExecute()
            executeOnly()
            visualizeOnly()
            NoAny()
            showpulse()
*/

class GraphicsManager {
  private final int WINDOW_SIZE_X = 1000;   //length of the window
  private final int WINDOW_SIZE_Y = 900;    //height of the window
  
  JSONArray  coordinates;
  JSONArray  electrodes;
  float[][]  electrodePositions;

  //Setup the Window
  void setupGraphics() {
    size(WINDOW_SIZE_X, WINDOW_SIZE_Y);
  }
  
  //Display the instructions for user
  void displayInstructions() {
    println("Now pusle height is set to 0. Press UP and DOWN keys to adjust volume.");
    println("Press RIGHT and LEFT keys to adjust pulse width.");
    println("Press p to change the polarity.");
    println("Press space_bar to reset pulse height and pulse width");
  }
  
  //Reset the electrodes
  void drawElectrodes() {
    electrodePositions = new float[dataLoader.electrodes_number][2];
    
    noStroke();
    textSize(27);
    
    for (int i=0; i < dataLoader.electrodes.size(); i++){
      JSONObject  electrode  = dataLoader.electrodes.getJSONObject(i);
      
      float x,y;
      
      if (needToScale){
        x          = (electrode.getFloat("x") * scaleFactor) * 10 + 500;
        y          = 900-((electrode.getFloat("y") * scaleFactor) * 10 + 500);
        electrodeSize = 2 * (dataLoader.electrodeRadius) * scaleFactor * 5;
      }
      else{
        x          = electrode.getFloat("x") * 10 + 500;
        y          = 900-(electrode.getFloat("y") * 10 + 500);
        electrodeSize = 2 * (dataLoader.electrodeRadius) * 5;
      }
      int         number     = dataLoader.mapping_func[i];
      
      electrodePositions[i][0] = x;
      electrodePositions[i][1] = y;
      
      
      if(on_board){
        if (eTactile.switch_state[i+24] == 1){
          if (eTactile.voltages[i] <= 60 + eTactile.stimulation_pulse_height && eTactile.voltages[i] >= 20 && disp_elecs_values){
            stroke(0,255,0);
          } else{
            noStroke();
          }
          fill(255,0,0);
        }
        else{
          if (eTactile.voltages[i] <= 80 && eTactile.voltages[i] >= 20 && disp_elecs_values){
            stroke(0,255,0);
          } else{
            noStroke();
          }
          fill(0,0,255);
        }
    }
      
      else{
          if (eTactile.switch_state[i] == 1){
            if (eTactile.voltages[i] <= 60 + eTactile.stimulation_pulse_height && eTactile.voltages[i] >= 20 && disp_elecs_values){
              stroke(0,255,0);
            } else{
              noStroke();
            }
            fill(255,0,0);
          }
        else{
          if (eTactile.voltages[i] <= 80 && eTactile.voltages[i] >= 20 && disp_elecs_values){
            stroke(0,255,0);
          } else{
            noStroke();
          }
          fill(0,0,255);
        }
      }
      
      
      ellipseMode(CENTER);
      ellipse(x, y, electrodeSize, electrodeSize);
      
      if(show_numbers){
        textSize(12);
        fill(255,255,255);
        text(number, x-4, y+2);
      }
      fill(0,0,255);
      textSize(27);
    }
    noStroke();
  }
  
  
  void visualizeBoardShape() {
      // Set color for the shape outline
      stroke(0);
      strokeWeight(2);
      fill(200, 200, 200); 
      
      // Initialize min and max values
      float x_min = Float.MAX_VALUE;
      float x_max = Float.MIN_VALUE;
      float y_min = Float.MAX_VALUE;
      float y_max = Float.MIN_VALUE;
      
      // First pass: Calculate min and max values of x and y
      for (int i = 0; i < dataLoader.coordinates.size(); i++) {
          JSONObject point = dataLoader.coordinates.getJSONObject(i);
          float x = point.getFloat("x") * 10 + 500;
          float y = 900 - (point.getFloat("y") * 10 + 500);
          
          if (x < x_min) x_min = x;
          if (x > x_max) x_max = x;
          if (y < y_min) y_min = y;
          if (y > y_max) y_max = y;
      }
      
      // Determine if scaling is needed
      boolean scaleX = (x_min < 180 || x_max > 830);
      boolean scaleY = (y_min < 130 || y_max > 670);
      
      // Calculate scaling factors
      float scaleFactorX = 1.0;
      float scaleFactorY = 1.0;
      
      if (scaleX) {
          float desiredWidth = 830 - 180;
          float currentWidth = x_max - x_min;
          scaleFactorX = desiredWidth / currentWidth;
      }
      
      if (scaleY) {
          float desiredHeight = 670 - 130;
          float currentHeight = y_max - y_min;
          scaleFactorY = desiredHeight / currentHeight;
      }
      
      // Use the smaller scaling factor to maintain aspect ratio
      scaleFactor = min(scaleFactorX, scaleFactorY);
      
      // Start drawing the shape
      beginShape();
      
      // Second pass: Add scaled vertices to the shape
      for (int i = 0; i < dataLoader.coordinates.size(); i++) {
          JSONObject point = dataLoader.coordinates.getJSONObject(i);
          
          if (scaleX || scaleY){
            needToScale = true;
            float x = (point.getFloat("x") * scaleFactor) * 10 + 500;
            float y = 900 - ((point.getFloat("y") * scaleFactor) * 10 + 500);
            
            vertex(x, y); // Add each vertex
          }
          
          else{
            float x = point.getFloat("x") * 10 + 500;
            float y = 900 - (point.getFloat("y") * 10 + 500);
            
            vertex(x, y); // Add each vertex
          }
          
          
          
      }
      
      // End and close the shape
      endShape(CLOSE);
  }
  

  
  //If execution: true & simulation: true
  void visualizeAndExecute(){
    textSize(20);
    fill(255);
    int amplitude = eTactile.stimulation_pulse_height;
    int width_    = eTactile.stimulation_pulse_width;
    text("Amplitude: " + amplitude, 20, WINDOW_SIZE_Y - 60);
    text("Pulse Width: " + width_, 20, WINDOW_SIZE_Y - 30);
  }
  
  //If execution: true & simulation: false
  void executeOnly(){
    int amplitude = eTactile.stimulation_pulse_height;
    int width_    = eTactile.stimulation_pulse_width;
    textSize(40);
    fill(255);
    text("No Visualization. Execution Only.", 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2);
    text("Amplitude: " + amplitude, 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2 + 60);
    text("Pulse Width: " + width_, 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2 + 90);
    
    text("Sense Height: " + eTactile.sense_pulse_height, 750, WINDOW_SIZE_Y - 60);
    text("Sense Width: " + eTactile.sense_pulse_width, 750, WINDOW_SIZE_Y - 30);
  }
  
  //If execution: false & simulation: true
  void visualizeOnly(){
    textSize(32);
    fill(255);
    text("No execution. Visualization Only", WINDOW_SIZE_X / 5, WINDOW_SIZE_Y - 60);
    noStroke();
    textSize(27);
  }
  
  //If execution: false & simulation: true
  void noAny(){
    textSize(32);
    fill(255);
    text("No execution or Visualization activated!", 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2.5);
    textSize(28);
    text("Please check your .json (pattern) file", 5 * WINDOW_SIZE_X / 25, WINDOW_SIZE_Y / 2);
  }
  
  //Visual indicator of the pules height and pulse width
  void showPulse(){
    int amplitude  = eTactile.stimulation_pulse_height; //eTactile.amplitude;
    int width_     = eTactile.stimulation_pulse_width; //eTactile.width_;
    int h,w;
    noFill();
    stroke(0,255,0);
    strokeWeight(4);
    h = WINDOW_SIZE_Y * amplitude / (260*10);
    w = WINDOW_SIZE_X/2*width_/(1000*3);
    rect(180,WINDOW_SIZE_Y-h,w,h);
    textSize(28);
  }
  
  void showSensePulse(){
    int amplitude  = eTactile.sense_pulse_height; //eTactile.amplitude;
    int width_     = eTactile.sense_pulse_width; //eTactile.width_;
    int h,w;
    noFill();
    stroke(0,255,0);
    strokeWeight(4);
    h = WINDOW_SIZE_Y * amplitude / (260*10);
    w = WINDOW_SIZE_X/2*width_/(1000*3);
    rect(930,WINDOW_SIZE_Y-h,w,h);
    
    
    textSize(20);
    text("Sense Height: " + eTactile.sense_pulse_height, 750, WINDOW_SIZE_Y - 60);
    text("Sense Width: " + eTactile.sense_pulse_width, 750, WINDOW_SIZE_Y - 30);
    textSize(28);
  }
  
  void showCalibratingPulse(){
    int amplitude  = eTactile.stimulation_pulse_height;
    int width_     = eTactile.stimulation_pulse_width;
    int h,w;
    noFill();
    stroke(0,255,0);
    strokeWeight(4);
    h = WINDOW_SIZE_Y * amplitude / (260*10);
    w = WINDOW_SIZE_X/2*width_/(1000*3);
    rect(180,WINDOW_SIZE_Y-h,w,h);
    textSize(28);
  }
  
  /*float[] getElectrodePosition(int index){
    electrodePositions = new float[dataLoader.electrodes_number][2];
    return electrodePositions[index];
  }*/
  
}
