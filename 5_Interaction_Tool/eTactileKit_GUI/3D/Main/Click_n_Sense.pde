
class ClickNSense {
  
  
  int currentElectrode;
  int[][] electrodeValues;
  float[][] electrodePositions; // Store positions
  float[][] electrodeScreenPositions;
  int low_tresh_sum;
  color[] electrodeColors;
  byte[] SwitchState;
  byte[] SwitchState_zero;
  int[] ElectrodeMapping;
  int ELECTRODE_NUM;
  boolean isCalibrating;
  int intensity;
  int volume = 0, width_ = 0;
  boolean calibrationComplete;
  SerialComm serialComm;
  boolean flag;

  int lastUpdateTime; // Variable to track last update time
  int calibrationInterval; // Interval for increasing intensity (in milliseconds)
  boolean counter = true;
  int couner_interval = 500;

  PApplet parent;
  
  ClickNSense(PApplet parent){
    this.parent = parent;
    }

  
   public void SETUP3D(String json_array, String COM_PORT, String Object3D){
      println("Setting up eTactileKit");
      keyHandler       = new KeyPressHandler();
      dataLoader       = new LoadData();
      dataLoader.load3DObjArray(json_array, Object3D);
      
      
      //Initialize Serial Communication if the execution is true in JSON pattern data
      if (DEBUG != 0 && !serialIntialized) {
        mySerialComm   = new SerialComm(parent, COM_PORT);
        serialIntialized = true;
      }
      
      frameRate(60);
      
      ElectrodeMapping = dataLoader.mapping_func;
      ELECTRODE_NUM = dataLoader.electrodes_number;
      
      currentElectrode = 0;
      electrodeValues = new int[ELECTRODE_NUM][2];
      electrodeColors = new color[ELECTRODE_NUM];
      SwitchState = new byte[ELECTRODE_NUM];
      SwitchState_zero = new byte[ELECTRODE_NUM];
      flag = true;
      electrodePositions = new float[dataLoader.electrodes_number][3];
      electrodeScreenPositions = new float[dataLoader.electrodes_number][2];
     
      
      
      
      
      // Print electrode mapping
      System.out.println("Electrode Mapping:");
      for (int ch = 0; ch < ElectrodeMapping.length; ch++) {
          System.out.println("Channel " + ch + " -> Electrode " + ElectrodeMapping[ch]);
      }
      
      // Initialize all electrode colors to gray
      for (int i = 0; i < electrodeColors.length; i++) {
        electrodeColors[i] = color(0, 0, 255); // Gray color before calibration
      }
  
      
      // Loop through the electrode points and draw each as a circle
      for (int i = 0; i < dataLoader.electrodes.size(); i++) {
        JSONObject electrode = dataLoader.electrodes.getJSONObject(i);
        float x = electrode.getFloat("x");
        float y = electrode.getFloat("y");
        float z = electrode.getFloat("z");
        
        electrodePositions[i][0] = x; // Store x position
        electrodePositions[i][1] = y; // Store y position
        electrodePositions[i][2] = z; // Store z position
      }
      lastUpdateTime = millis(); 
      
       //Setting the parameters for the stimulation
    if (DEBUG != 0 && dataLoader.execution) {
      println("Sending commands");
      eTactile.send_electrode_number(dataLoader.electrodes_number);
      eTactile.send_stimulation_polarity(1);
      eTactile.send_stimulation_pulse_height(0);
      eTactile.send_stimulation_pulse_width(50);
      eTactile.send_sense_pulse_height(0);
      eTactile.send_sense_pulse_width(0);
      eTactile.send_channel_discharge_time(50);
      eTactile.send_stimulation_frequency(75);
    }
      println("Click and Sense initiated");
  }
  
 void click_N_Sense() {
    viewport.beginDraw();
    viewport.background(25);
    viewport.pushMatrix();
    viewport.translate((viewportWidth / 2) + positionX, (height / 2) + positionY);
    viewport.scale(zoom);
    viewport.rotateX(angleX);
    viewport.rotateY(angleY);
    viewport.fill(100);
    
    graphicsManager.visualize3DObject();
    graphicsManager.showPulse();
    graphicsManager.visualizeAndExecute();

    int currentTime = millis();
    if (currentTime - lastUpdateTime >= couner_interval) {
        counter = !counter;
        lastUpdateTime = currentTime; // Update last update time
    }

    volume = keyHandler.volume;
    width_ = keyHandler.width_;

    for (int i = 0; i < electrodeValues.length; i++) {
        float[] pos = electrodePositions[i];
        float electrodeX = pos[0];
        float electrodeY = pos[1];
        float electrodeZ = pos[2];

        // Check if the electrode is blinking
        if (SwitchState[i] == 1 && counter) {
            intensity = volume;
            eTactile.send_stim_pattern(SwitchState);
        } else {
            intensity = 0;
            eTactile.send_stim_pattern(SwitchState_zero);
        }

        // Update the electrode color based on intensity
        color electrodeColor = calculateGradientColor(intensity);
        electrodeColors[i] = electrodeColor;

        // Draw the electrode
        viewport.stroke(0); // Set stroke to black (or any preferred color)
        viewport.strokeWeight(0); // Set stroke thickness
        viewport.pushMatrix();
        viewport.fill(electrodeColors[i]);
        viewport.translate(electrodeX, electrodeY, electrodeZ);
        viewport.sphere(dataLoader.electrodeRadius); // Draw small spheres for electrodes
        viewport.popMatrix();

        // Update real-time electrode positions (x, y) on the screen
        float screenX = viewport.screenX(electrodeX, electrodeY, electrodeZ);
        float screenY = viewport.screenY(electrodeX, electrodeY, electrodeZ);
        electrodeScreenPositions[i][0] = screenX;
        electrodeScreenPositions[i][1] = screenY;
    }
    
    viewport.popMatrix();
    viewport.endDraw();
    image(viewport, 0, 0);
    fill(255);
}

void handleMousePressed(float mouseX, float mouseY) {
    for (int i = 0; i < electrodeScreenPositions.length; i++) {
        float[] pos = electrodeScreenPositions[i];
        float electrodeScreenX = pos[0];
        float electrodeScreenY = pos[1];

        if (dist(mouseX, mouseY, electrodeScreenX, electrodeScreenY) < 5) { // Radius = 12.5
            SwitchState[i] = (byte)((SwitchState[i] == 1) ? 0 : 1);
            println("Electrode " + i + " toggled to " + (SwitchState[i] == 1 ? "ON" : "OFF"));
            break;
        }
    }
    
    //eTactile.send_stim_pattern(SwitchState);
}

  color calculateGradientColor(int intensity) {
    // Define color ranges
    color grayColor = color(128, 180, 128); // Gray
    color lightGreenColor = color(144, 238, 144); // Light Green
    color greenColor = color(0, 255, 0); // Green
    color redColor = color(255, 0, 0); // Red

    // Map intensity to gradient
    if (intensity*width_ <= 50*50) {
        // Transition from Gray to Green
        if (intensity*width_ <= 25*50) {
            // From Gray to Light Green
            return lerpColor(grayColor, lightGreenColor, map(intensity, 0, 25, 0, 1));
        } else {
            // From Light Green to Green
            return lerpColor(lightGreenColor, greenColor, map(intensity, 25, 50, 0, 1));
        }
    } else {
        // Transition from Green to Red
        float ratio = map(intensity, 50, 100, 0, 1); // Map intensity to 0–1 range
        return lerpColor(greenColor, redColor, ratio);
    }
  }
}
