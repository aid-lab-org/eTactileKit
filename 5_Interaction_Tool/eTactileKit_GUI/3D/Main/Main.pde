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
boolean valid_obj = true;

int     local_timer = 0;

int lower_thresh_hight, lower_thresh_width;
int upper_thresh_hight, upper_thresh_width;

String[] availableCOMPorts;
String selectedCOMPort;
String selectedStimulationPattern;
String selectedArrayPattern;
String selected3DObject;

String pattern;
String array_;
String object;

int start_elec;
int end_elec;
boolean disp_elecs_values = false;
boolean show_numbers = false;

PGraphics viewport;
float angleX = 0, angleY = 0;
float zoom = 1;
float positionX = 0, positionY = 0;

int viewportWidth;
float obj_width, obj_height, obj_depth;

PImage logo;

boolean override = false;

boolean pattern_selected = false;
boolean general_check = false;

boolean on_board = false;

void settings() {
  graphicsManager = new GraphicsManager();
  graphicsManager.setupGraphics();
}

void setup() {
  viewportWidth = 700; // Half of the screen for 3D view
  viewport = createGraphics(viewportWidth, 900, P3D);
  
  eTactile = new ETactile(this);
  uiManager = new UIManager(this);
  uiManager.setupPage1();
  
  logo = loadImage("Image/Logo.png");
  
}

void draw() {
  background(0);
  if (currentPage == 1) {
    uiManager.drawPage1();
    uiManager.drawViewportPage();
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
  //eTactile.updatePulse();
}

void initializeETactile() {
  
  if (calibration_ && !confirm){
    //proceed_et = true;
    uiManager.showCalibrationSummaryDialog(lower_thresh_hight, lower_thresh_width, upper_thresh_hight, upper_thresh_width);
    return;
  }
 

  if (selectedArrayPattern != null && selected3DObject != null) {
    
    
    eTactile.SETUP3D(selectedArrayPattern, selectedCOMPort, selected3DObject);
    
    if (valid_files_array && valid_obj){
      
      if (!proceed_et) {
        uiManager.showWarningDialog(); // Show the warning dialog
        return; // Exit the method to prevent further execution
      }
    
      println("eTactile initialized with:");
      println("COM Port: " + selectedCOMPort);
      println("Stimulation Pattern: " + selectedStimulationPattern);
      println("Array Pattern: " + selectedArrayPattern);
  
      if (currentPage == 2) {
        uiManager.hidePage2UI();
      } else if (currentPage == 1) {
        uiManager.hidePage1UI();
      } else if (currentPage == 4){
        uiManager.hidePage4UI();
      }
  
      // Move to Page 3
      currentPage = 3;
      uiManager.setupPage3();
    } else if (!valid_files_array){
      uiManager.showArrayFileErrorDialog();
      println("Please select valid JSON files");
      valid_files_array = true;
    }
    else{
      uiManager.showObjectErrorDialog();
      println("Please select valid object files");
      valid_obj = true;
    }
  } else {
    if (selectedArrayPattern == null && selected3DObject != null){
    uiManager.showArrayInitializationErrorDialog();
    println("Please select an Array before initializing.");
    } else if (selectedArrayPattern != null && selected3DObject == null){
      uiManager.showObjInitializationErrorDialog();
      println("Please select an Object before initializing.");
    } else{
      uiManager.showInitializationErrorDialog();
      println("Please select an Array & Object files before initializing.");
    }
  }
}

void initializeCalibration(){
  calibrator = new Calibrator(this);
  calibrator.SETUP3D(selectedArrayPattern, selectedCOMPort, selected3DObject);
  
  currentPage = 2;
  uiManager.setupPage2();
  uiManager.hidePage1UI();
  calibration_ = true;
  confirm = false;
  allowed = false; 
}

void Click_n_Sense(){
  click_n_sense = new ClickNSense(this);
  click_n_sense.SETUP3D(selectedArrayPattern, selectedCOMPort, selected3DObject);
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

// void mouseDragged() {
//   if (mouseX < viewportWidth) {
//     angleY += (mouseX - pmouseX) * 0.01;
//     angleX -= (mouseY - pmouseY) * 0.01;
//   }
// }

void mouseDragged() {
  if (mouseX < viewportWidth) {
    if (mouseButton == LEFT) {
      angleY += (mouseX - pmouseX) * 0.01;
      angleX -= (mouseY - pmouseY) * 0.01;
    } else if (mouseButton == RIGHT) {
      float dx = (mouseX - pmouseX) * 0.5;
      float dy = (mouseY - pmouseY) * 0.5;
      positionX += dx;
      positionY += dy;
      // println("Position X: " + positionX + ", Position Y: " + positionY);
    }
  }
}

void mouseWheel(MouseEvent event) {
  if (mouseX < viewportWidth) {
    zoom -= event.getCount() * 0.1;
    zoom = constrain(zoom, 0.1, 10);
  }
}

// Function to toggle override and update button color
void toggleOverride() {
    override = !override; // Toggle the boolean variable
    //println("override: ", override);
    uiManager.updateOverrideButton(); // Update the button's color
}
