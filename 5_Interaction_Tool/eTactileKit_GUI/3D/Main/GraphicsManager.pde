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
  private final int WINDOW_SIZE_X = 1350;   //length of the window
  private final int WINDOW_SIZE_Y = 900;    //height of the window
  
  JSONArray  coordinates;
  JSONArray  electrodes;
  float[][]  electrodePositions;

  //Setup the Window
  void setupGraphics() {
    size(WINDOW_SIZE_X, WINDOW_SIZE_Y,P3D);
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
    electrodePositions = new float[dataLoader.electrodes_number][3];
    
    viewport.noStroke();
    viewport.textSize(27);
    
    for (int i=0; i < dataLoader.electrodes.size(); i++){
      JSONObject  electrode  = dataLoader.electrodes.getJSONObject(i);
      float       x          = electrode.getFloat("x");
      float       y          = electrode.getFloat("y");
      float       z          = electrode.getFloat("z");
      int         number     = i;
      
      electrodePositions[i][0] = x;
      electrodePositions[i][1] = y;
      electrodePositions[i][2] = z;
      
      if (eTactile.switch_state[i] == 1){
        if (eTactile.voltages[i] <= 60 + eTactile.stimulation_pulse_height && eTactile.voltages[i] >= 20 && disp_elecs_values){
          viewport.fill(255,150,0);
        } else{
        viewport.fill(255,0,0);
        }
      }
      else{
        if (eTactile.voltages[i] <= 80 && eTactile.voltages[i] >= 20 && disp_elecs_values){
        viewport.fill(0,200,255);
        }
        else{
          viewport.fill(0,0,255);
        }
      }
      
      viewport.textSize(15);
      viewport.pushMatrix();
      viewport.translate(x, y, z);
      viewport.sphere(dataLoader.electrodeRadius); // Draw small spheres for electrodes
      viewport.popMatrix();
      viewport.textSize(27);
    }
  }
  
  

  
  //If execution: true & simulation: true
  void visualizeAndExecute(){
    textSize(18);
    int amplitude = keyHandler.getVolume();
    int width_    = keyHandler.getWidth();
    text("Amplitude: " + amplitude, viewportWidth+50, 755);
    text("Pulse Width: " + width_, viewportWidth+50, 780);
  }
  
  //If execution: true & simulation: false
  void executeOnly(){
    int amplitude = keyHandler.getVolume();
    int width_    = keyHandler.getWidth();
    textSize(40);
    text("No Visualization. Execution Only.", 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2);
    text("Amplitude: " + amplitude, 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2 + 60);
    text("Pulse Width: " + width_, 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2 + 90);
    
  }
  
  //If execution: false & simulation: true
  void visualizeOnly(){
    textSize(32);
    text("No execution. Visualization Only", WINDOW_SIZE_X / 5, WINDOW_SIZE_Y - 60);
    noStroke();
    textSize(27);
  }
  
  //If execution: false & simulation: true
  void noAny(){
    textSize(32);
    text("No execution or Visualization activated!", 5 * WINDOW_SIZE_X / 32, WINDOW_SIZE_Y / 2.5);
    textSize(28);
    text("Please check your .json (pattern) file", 5 * WINDOW_SIZE_X / 25, WINDOW_SIZE_Y / 2);
  }
  
  //Visual indicator of the pules height and pulse width
  void showPulse(){
    int amplitude  = keyHandler.volume; //eTactile.amplitude;
    int width_     = keyHandler.width_; //eTactile.width_;
    int h,w;
    noFill();
    stroke(0,255,0);
    strokeWeight(4);
    h = WINDOW_SIZE_Y * amplitude / (260*10);
    w = WINDOW_SIZE_X/2*width_/(1000*3);
    rect(viewportWidth+100,WINDOW_SIZE_Y-h,w,h);
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
    rect(viewportWidth+450,WINDOW_SIZE_Y-h,w,h);
    
    
    textSize(18);
    text("Sense Height: " + eTactile.sense_pulse_height, viewportWidth+350, 755);
    text("Sense Width: " + eTactile.sense_pulse_width, viewportWidth+350, 780);
    textSize(28);
  }
  
  void showCalibratingPulse(){
    int amplitude  = keyHandler.volume;
    int width_     = keyHandler.width_;
    int h,w;
    noFill();
    stroke(0,255,0);
    strokeWeight(4);
    h = WINDOW_SIZE_Y * amplitude / (260*10);
    w = WINDOW_SIZE_X/2*width_/(1000*3);
    rect(viewportWidth+100,WINDOW_SIZE_Y-h,w,h);
    textSize(28);
  }
  
  void visualize3DObject() {
    // println("visualizing");
    pushMatrix(); 
    viewport.fill(100);
    viewport.shape(dataLoader.objShape);
    // println("visualizing done");
    popMatrix();
  }
  
}
