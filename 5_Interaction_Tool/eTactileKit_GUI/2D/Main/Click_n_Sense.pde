
class ClickNSense {
  
  
  int currentElectrode;
  int[][] electrodeValues;
  float[][] electrodePositions; // Store positions
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

  
   public void SETUP(String json_array, String COM_PORT){
      println("Setting up eTactileKit");
      keyHandler       = new KeyPressHandler();
      dataLoader       = new LoadData();
      dataLoader.loadArray(json_array);
      
      
      //Initialize Serial Communication if the execution is true in JSON pattern data
      if (DEBUG != 0 && dataLoader.execution && !serialIntialized) {
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
      electrodePositions = new float[dataLoader.electrodes_number][2];
     
      // Print electrode mapping
      System.out.println("Electrode Mapping:");
      for (int ch = 0; ch < ElectrodeMapping.length; ch++) {
          System.out.println("Channel " + ch + " -> Electrode " + ElectrodeMapping[ch]);
      }
      
      // Initialize all electrode colors to gray
      for (int i = 0; i < electrodeColors.length; i++) {
        electrodeColors[i] = color(0, 0, 255); // Gray color before calibration
      }
  
      graphicsManager.visualizeBoardShape();
      // Loop through the electrode points and draw each as a circle
      for (int i = 0; i < dataLoader.electrodes.size(); i++) {
        JSONObject electrode = dataLoader.electrodes.getJSONObject(i);
        
        float x,y;
        
        if (needToScale){
          x = (electrode.getFloat("x") * scaleFactor) * 10 + 500;
          y = 900 - ((electrode.getFloat("y") * scaleFactor) * 10 + 500);
          electrodeSize = 2 * (dataLoader.electrodeRadius) * scaleFactor * 5;
        }
        
        else {
          x = electrode.getFloat("x") * 10 + 500;
          y = 900 - (electrode.getFloat("y") * 10 + 500);
          electrodeSize = 2 * (dataLoader.electrodeRadius) * 5;
        }
        
        electrodePositions[i][0] = x; // Store x position
        electrodePositions[i][1] = y; // Store y position
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
    graphicsManager.visualizeBoardShape();
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
        stroke(0); // Black border
        strokeWeight(1);
        fill(electrodeColors[i]);
        ellipse(electrodeX, electrodeY, electrodeSize, electrodeSize);
    }
}

    void handleMousePressed(float mouseX, float mouseY) {
        for (int i = 0; i < electrodePositions.length; i++) {
            float[] pos = electrodePositions[i];
            float electrodeX = pos[0];
            float electrodeY = pos[1];

            if (dist(mouseX, mouseY, electrodeX, electrodeY) < electrodeSize/2) { // Radius
                SwitchState[i] = (byte)((SwitchState[i] == 1) ? 0 : 1);
                println("Electrode " + i + " toggled to " + (SwitchState[i] == 1 ? "ON" : "OFF"));
                break;
            }
        }
        
    }

  color calculateGradientColor(int intensity) {
    // Define color ranges
    color grayColor = color(128, 128, 128); // Gray
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
