import controlP5.*;
import java.io.File;
import java.util.List;
import java.util.ArrayList;
import processing.serial.*;

final private int DEBUG = 1;

ControlP5 cp5;
LoadData dataLoader;
KeyPressHandler keyHandler;
GraphicsManager graphicsManager;
SerialComm mySerialComm;
ETactile eTactile;
UIManager uiManager;
Calibrator calibrator;
ClickNSense click_n_sense;

boolean isRunning = false;
int currentPage = 1; // 1 for the first page, 2 for the second page
boolean calibration_ = false;
boolean proceed_et = false;
boolean confirm = false;
boolean allowed = false;
boolean serialIntialized = false;
boolean valid_files_array = true;
boolean valid_files_pattern = true;

int     local_timer = 0;

int lower_thresh_hight, lower_thresh_width;
int upper_thresh_hight, upper_thresh_width;

String[] availableCOMPorts;
String selectedCOMPort;
String selectedStimulationPattern;
String selectedArrayPattern;

float scaleFactor;
boolean needToScale = false;
float electrodeSize;

String pattern;
String array_;

int start_elec;
int end_elec;
boolean disp_elecs_values = false;
boolean show_numbers = false;

boolean override = false;

boolean pattern_selected = false;
boolean general_check = false;

void settings() {
  graphicsManager = new GraphicsManager();
  graphicsManager.setupGraphics();
}

void setup() {
  eTactile = new ETactile(this);
  uiManager = new UIManager(this);
  uiManager.setupPage1();
}

void draw() {
  background(0);
  if (currentPage == 1) {
    drawGradientBackground();
    uiManager.drawPage1();
    availableCOMPorts = Serial.list();
  } else if(currentPage == 2 && calibration_){
    uiManager.drawPage2();
    calibrator.calibrate();
  }else if (currentPage == 3) {
    uiManager.drawPage3();
    if (isRunning) {
      eTactile.stimulate(selectedStimulationPattern);
    }
  }else if (currentPage == 4){
    uiManager.drawPage4();
    click_n_sense.click_N_Sense();
  }
  delay(1);
}

void keyPressed() {
  keyHandler.handleKeyPress(key);
  // eTactile.updatePulse();
}

void initializeETactile() {
  
  if (calibration_ && !confirm){
    //proceed_et = true;
    uiManager.showCalibrationSummaryDialog(lower_thresh_hight, lower_thresh_width, upper_thresh_hight, upper_thresh_width);
    return;
  }
  
 

  if (selectedArrayPattern != null) {
    
    
    eTactile.SETUP(selectedArrayPattern, selectedCOMPort);
    
    if (valid_files_array){
      
      if (!proceed_et) {
        uiManager.showWarningDialog(); // Show the warning dialog
        return; // Exit the method to prevent further execution
      }
        println("eTactile initialized with:");
        println("COM Port: " + selectedCOMPort);
        println("Stimulation Pattern: " + selectedStimulationPattern);
        println("Array Pattern: " + selectedArrayPattern);
    
        if (currentPage == 2) {
          // mySerialComm.closePort();
          uiManager.hidePage2UI();
        } else if (currentPage == 1) {
          uiManager.hidePage1UI();
        } else if (currentPage == 4){
          uiManager.hidePage4UI();
        }
    
        // Move to Page 3
        currentPage = 3;
        uiManager.setupPage3();
    }else{
      uiManager.showArrayFileErrorDialog();
      println("Please select valid JSON files");
      valid_files_array = true;
    }
   
    
  } else {
    uiManager.showArrayInitializationErrorDialog();
    println("Please Select an Electrode Array before initializing.");
  }
}

void initializeCalibration(){
  calibrator = new Calibrator(this);
  calibrator.SETUP(selectedArrayPattern, selectedCOMPort);
  
  currentPage = 2;
  uiManager.setupPage2();
  uiManager.hidePage1UI();
  calibration_ = true;
  confirm = false;
  allowed = false;
  
}

void Click_n_Sense(){
  click_n_sense = new ClickNSense(this);
  click_n_sense.SETUP(selectedArrayPattern, selectedCOMPort);
  currentPage = 4;
  uiManager.setupPage4();
  uiManager.hidePage1UI();
  //calibration_ = true;
}



void setLowerTreshold(int volume, int pulse_width){
  lower_thresh_hight = volume;
  lower_thresh_width = pulse_width;
  println("lower hight: ", lower_thresh_hight,"lower width: ", lower_thresh_width );
  stroke(255);
  //text("Lower thershold", 335, 750);
  //text("Pulse height: "+lower_thresh_hight, 335, 775);
  //text("Pulse width: "+lower_thresh_width, 335, 800);
  println("lower");
}


void setUpperTreshold(int volume, int pulse_width){
  upper_thresh_hight = volume;
  upper_thresh_width = pulse_width;
  println("higher hight: ", upper_thresh_hight,"higher width: ", upper_thresh_width );
  //text("Upper thershold", 535, 750);
  //text("Upper height: "+upper_thresh_hight, 535, 775);
  //text("Upper width: "+upper_thresh_width, 535, 800);
}


void toggleStartStop() {
  isRunning = !isRunning;
  uiManager.updateButtonLabel(isRunning);
  if (isRunning){
    if (selectedStimulationPattern != null){
    local_timer = 0;
    println("Program started.");
    } else{
        uiManager.showPatternInitializationErrorDialog();
        println("Please Select a Stimulation pattern before initializing.");
        toggleStartStop();
      }
  }
  else{
    if (calibration_){
      allowed = false;
    }
    eTactile.resetElectrodes();
    pattern_selected = false;
    println("Program stopped.");
  }
}

void electrodes_start_check(int electrode){
 if (electrode < 0 || electrode > dataLoader.electrodes_number-1) {
   uiManager.outOfRangeError();
 }
 else{
   start_elec = electrode;
 }
}

void electrodes_end_check(int electrode){
 if (electrode < 0 || electrode > dataLoader.electrodes_number-1) {
   uiManager.outOfRangeError();
 }
 else{
   end_elec = electrode;
 }
}

void display_elecs_values(){
  disp_elecs_values  = !disp_elecs_values;
}

void show_hide_numbers(){
  show_numbers  = !show_numbers;
}


String[] listJSONFiles(String directory) {
  File folder = new File(directory);
  List<String> jsonFiles = new ArrayList<>();
  if (folder.exists() && folder.isDirectory()) {
    for (File file : folder.listFiles()) {
      if (file.getName().endsWith(".json")) {
        jsonFiles.add(file.getName());
      }
    }
  }
  return jsonFiles.toArray(new String[0]);
}

void mousePressed() {
  if (currentPage == 4){
    click_n_sense.handleMousePressed(mouseX, mouseY); // Delegate to ClickNSense
  }
}

// Gradient background (black to blue)
void drawGradientBackground() {
  for (int i = 0; i < height; i++) {
    float inter = map(i, 0, height, 0, 1);
    color c = lerpColor(color(0, 0, 0), color(0, 50, 150), inter);
    stroke(c);
    line(0, i, width, i);
  }
}

// Function to toggle override and update button color
void toggleOverride() {
    override = !override; // Toggle the boolean variable
    //println("override: ", override);
    uiManager.updateOverrideButton(); // Update the button's color
}
