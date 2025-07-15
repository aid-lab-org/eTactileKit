import processing.data.*;
import java.util.Arrays;

class Calibrator {
  
  int currentElectrode;
  int[][] electrodeValues;
  float[][] electrodePositions; // Store positions
  int low_tresh_sum;
  color[] electrodeColors;
  byte[] SwitchState;
  int[] ElectrodeMapping;
  int ELECTRODE_NUM;
  boolean isCalibrating;
  int intensity;
  int volume = 0, width_ = 0;
  boolean calibrationComplete;
  boolean flag;

  int lastUpdateTime; // Variable to track last update time
  int calibrationInterval; // Interval for increasing intensity (in milliseconds)
  boolean counter = true;
  int couner_interval = 500;
  
  PApplet parent;
  
  Calibrator(PApplet parent){
    this.parent = parent;
    }

  
   public void SETUP(String json_array, String COM_PORT){
      println("Setting up Calibrator");
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
      low_tresh_sum = 0;
      isCalibrating = false;
      intensity = 0;
      //increment = 1;  // Slow increment rate
      calibrationComplete = false;
      SwitchState = new byte[ELECTRODE_NUM];
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
        x = (electrode.getFloat("x") * scaleFactor)*10+500;
        y = 900-((electrode.getFloat("y") * scaleFactor) *10+500);
        electrodeSize = 2 * (dataLoader.electrodeRadius) * scaleFactor * 5;
        }
        
        else{
        x = electrode.getFloat("x")*10+500;
        y = 900-(electrode.getFloat("y")*10+500);
        electrodeSize = 2 * (dataLoader.electrodeRadius) * 5;
        }
        
        electrodePositions[i][0] = x; // Store x position
        electrodePositions[i][1] = y; // Store y position
      }
      lastUpdateTime = millis(); 

      // Intialize hardware for calibration mode
      eTactile.send_electrode_number(electrodeValues.length);
      eTactile.send_stimulation_pulse_height(0);
      eTactile.send_stimulation_pulse_width(50);
      // send_sense_pulse_height(5);
      // send_sense_pulse_width(50);
      eTactile.send_channel_discharge_time(50);
      eTactile.send_stimulation_frequency(75);
  }

  void calibrate() {
    if (calibrationComplete) {
      return; // Exit if calibration is complete
    }
    graphicsManager.visualizeBoardShape();
    graphicsManager.showCalibratingPulse();
    graphicsManager.visualizeAndExecute();
  
    int currentTime = millis();
    if (currentTime - lastUpdateTime >= couner_interval) {
      counter = !counter;
      lastUpdateTime = currentTime; // Update last update time
    }
    // Increase the intensity
    
    volume = keyHandler.volume;
    width_ = keyHandler.width_;
    //println("Intensity: ",intensity, " Width: ", width_);

    // Draw all electrodes
    
    for (int i = 0; i < electrodeValues.length; i++) {
      if (counter){
      SwitchState[i] = 1;
      intensity = volume;
      }
      else{
        SwitchState[i] = 0;
        intensity = 0;
      }
      float[] pos = electrodePositions[i]; // Get electrode position
      float electrodeX = pos[0];
      float electrodeY = pos[1];
      color electrodeColor = calculateGradientColor(intensity);
      electrodeColors[i] = electrodeColor;
      
      stroke(0); // Set stroke to black (or any preferred color)
      strokeWeight(1); // Set stroke thickness
      
      fill(electrodeColors[i]);
      
      ellipse(electrodeX, electrodeY, electrodeSize, electrodeSize); // Adjust size as necessary
    }
    
    eTactile.send_stimulation_pulse_height(volume);
    eTactile.send_stimulation_pulse_width(width_);
    eTactile.send_stim_pattern(SwitchState);
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
