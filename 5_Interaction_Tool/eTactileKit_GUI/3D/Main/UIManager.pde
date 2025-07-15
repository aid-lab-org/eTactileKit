import java.io.File;
import java.awt.FileDialog;
import java.awt.Frame;

boolean buttonPressed = false;
Button overrideButton; // Declare the button
Slider frequencySlider;
Toggle stimModeToggle;

class UIManager {
  ControlP5 cp5;
  PApplet parent;
  
  PImage img;
  

  UIManager(PApplet parent) {
    this.parent = parent;
    cp5 = new ControlP5(parent);
  }

  void setupPage1() {
    // Set ControlP5 Theme
    cp5.setColorForeground(parent.color(70, 130, 180));
    cp5.setColorBackground(parent.color(30, 144, 255));
    cp5.setColorActive(parent.color(100, 149, 237));
    //cp5.setColorLabel(parent.color(255));
    
    // Load the image
    
    img = parent.loadImage("Image/Logo.png"); // Specify the image file path
    

    // Dropdown for COM Port
    availableCOMPorts = Serial.list();
    if (availableCOMPorts.length == 0) {
      availableCOMPorts = new String[] { "No COM Ports Found" };
    }
    cp5.addScrollableList("COMPort")
       .setLabel("Select COM Port")
       .setPosition(viewportWidth+80, 250)
       .setSize(250, 300)
       .setBarHeight(20)  // Height of each item in the dropdown
       .setHeight(100)    // Height of the expanded dropdown
       //.setItems(availableCOMPorts)
       .setColorBackground(parent.color(100, 100, 100))  // Dark gray for background
       .setColorActive(parent.color(0, 100, 255))     // Bright blue for active item
       .setColorForeground(parent.color(255, 255, 255)) // White for text and foreground
       .onChange(event -> {
           int selectedIndex = (int) event.getController().getValue();
           if (selectedIndex >= Serial.list().length) {
               println("Invalid COM Port selection. Please Refresh!");
               uiManager.invalidComPortError();
               return;
           }
           selectedCOMPort = Serial.list()[selectedIndex];
           println("Selected COM Port: " + selectedCOMPort);
       });
       
         // Refresh COM port button
    cp5.addButton("refreshComPort")
       .setLabel("Refresh")
       .setPosition(viewportWidth+30, 250)
       .setSize(45, 20)
       .setColorForeground(parent.color(0, 0, 255))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(70, 130, 180))
       .onClick(event -> {
         cp5.get(ScrollableList.class, "COMPort").clear();  // Clear existing items
         cp5.get(ScrollableList.class, "COMPort").setItems(availableCOMPorts);  // Update with new items
       });


    // Button to browse for Array Pattern
    cp5.addButton("browseArrayPattern")
       .setLabel("Import Array JSON")
       .setPosition(viewportWidth+350, 325)
       .setSize(200, 50)
       .setColorForeground(parent.color(60, 179, 113))
       .setColorBackground(parent.color(34, 139, 34))
       .setColorActive(parent.color(50, 205, 50))
       .onClick(event -> {
           String filePath = browseFile("Select Array Pattern",sketchPath("")+"/JSON_Files/array");
           if (filePath != null) {
               selectedArrayPattern = filePath;
               println("Selected Array Pattern: " + selectedArrayPattern);
               array_ = new File(filePath).getName();
               
               // Update the button label to show the selected file name
               cp5.getController("browseArrayPattern").setLabel(array_);
           }
       });
     
     // Button to browse for 3D object    
    cp5.addButton("browse3DObject")
    .setLabel("Import 3D Object")
    .setPosition(viewportWidth + 350, 250)
    .setSize(200, 50)
    .setColorForeground(color(60, 179, 113))
    .setColorBackground(color(34, 139, 34))
    .setColorActive(color(50, 205, 50))
    .onClick(event -> {
      String filePath = browseFile("Select 3D Object",sketchPath("")+"/Object");
      if (filePath != null) {
          selected3DObject = filePath;
          println("Selected 3D object: " + selected3DObject);
          object = new File(filePath).getName();
          
          // Update the button label to show the selected file name
          cp5.getController("browse3DObject").setLabel(object);
      }
    });
        
    // Initialize Button
    cp5.addButton("initiateCalibration")
       .setLabel("Calibration")
       .setPosition(viewportWidth+250, 600)
       .setSize(140, 50)
       .setColorForeground(parent.color(0, 0, 255))
       .setColorBackground(parent.color(0, 144, 255))
       .setColorActive(parent.color(70, 130, 180))
       .onClick(event -> initializeCalibration());

    // Initialize Button
    cp5.addButton("initiateETactile")
       .setLabel("Initialize")
       .setPosition(viewportWidth+250, 675)
       .setSize(140, 50)
       .setColorForeground(parent.color(0, 0, 255))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(70, 130, 180))
       .onClick(event -> initializeETactile());
       
       
     // Initialize Button
    cp5.addButton("initiateClickNSense")
       .setLabel("Click & Sense")
       .setPosition(viewportWidth+250, 750)
       .setSize(140, 50)
       .setColorForeground(parent.color(0, 0, 255))
       .setColorBackground(parent.color(0, 144, 255))
       .setColorActive(parent.color(70, 130, 180))
       .onClick(event -> Click_n_Sense());
       
    // Hide the warning dialog initially
    if (cp5.getGroup("warningDialog") != null) {
      cp5.getGroup("warningDialog").hide();
    }
  }

  void setupPage3() {
    uiManager.setupPage3UI();
  }
  
  void setupPage2(){
    
    img = parent.loadImage("Image/Logo.png"); 
    
     cp5.addButton("setLowerTreshold")
       .setLabel("Set as Lower Threshold")
       .setPosition(viewportWidth+ 65, 450)
       .setSize(140, 50)
       .setColorForeground(parent.color(255, 99, 71))
       .setColorBackground(parent.color(255, 69, 0))
       .setColorActive(parent.color(255, 140, 0))
       .onClick(event -> setLowerTreshold(keyHandler.volume, keyHandler.width_));
       
     cp5.addButton("setUpperTreshold")
       .setLabel("Set as Upper Threshold")
       .setPosition(viewportWidth+315, 450)
       .setSize(140, 50)
       .setColorForeground(parent.color(255, 99, 71))
       .setColorBackground(parent.color(255, 69, 0))
       .setColorActive(parent.color(255, 140, 0))
       .onClick(event -> setUpperTreshold(keyHandler.volume, keyHandler.width_));
      
     // Initialize Button
    cp5.addButton("initiateETactile_2")
       .setLabel("Initialize")
       .setPosition(viewportWidth+315, 250)
       .setSize(140, 50)
       .setColorForeground(parent.color(0, 0, 255))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(70, 130, 180))
       .onClick(event -> initializeETactile());
       
     // Back Button
    cp5.addButton("backToPage1_2")
       .setLabel("Back to home")
       .setPosition(viewportWidth+ 65, 250)
       .setSize(140, 50)
       .setColorForeground(parent.color(70, 130, 180))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(100, 149, 237))
       .onClick(event -> {
         calibration_ = false;
         currentPage = 1; // Set back to Page 1
         hidePage2UI();
         resetToPage1();  // Reset the UI elements
       });
     
  }
  
  void setupPage4(){
    
    img = parent.loadImage("Image/Logo.png"); 
    
    // Initialize Button
    cp5.addButton("initiateETactile_3")
       .setLabel("Initialize")
       .setPosition(viewportWidth+315, 250)
       .setSize(140, 50)
       .setColorForeground(parent.color(0, 0, 255))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(70, 130, 180))
       .onClick(event -> initializeETactile());
       
    // Back Button
    cp5.addButton("backToPage1_4")
       .setLabel("Back to home")
       .setPosition(viewportWidth+65, 250)
       .setSize(140, 50)
       .setColorForeground(parent.color(70, 130, 180))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(100, 149, 237))
       .onClick(event -> {
         currentPage = 1; // Set back to Page 1
         hidePage4UI();
         resetToPage1();  // Reset the UI elements
       });
  }

  void drawPage1() {
    parent.textSize(32);
    parent.fill(255);
    parent.textAlign(PApplet.LEFT);
    parent.text("Select Configurations", 320, 350);
    
    int imgWidth = 881; 
    int imgHeight = 148; 
    float n = 0.4;
    parent.image(img, viewportWidth+80, 90, n*imgWidth, n*imgHeight);
  }

  void drawPage3() {
    parent.textSize(14);
    parent.text("Display readings", viewportWidth+400, 615);
    parent.textSize(18);
    parent.fill(255);
    parent.textAlign(PApplet.LEFT);
    //parent.text("Page 2: Summary and Start/Stop", 20, 30);
    parent.textSize(18);
    parent.text("COM Port: " + selectedCOMPort, viewportWidth+50, 400);
    parent.text("Select the pattern JSON:",viewportWidth+50, 450);
    //parent.text("Pattern: " + array_,  viewportWidth+50, 460);
    
    int imgWidth = 881; 
    int imgHeight = 148; 
    float n = 0.4;
    parent.image(img, viewportWidth+80, 90, n*imgWidth, n*imgHeight);
    
    // Display the current frequency value
    int frequency = eTactile.stimulation_frequency;
    parent.text("Frequency: " + int(frequency) + " Hz", viewportWidth+50, 555);
    
    // Display the current polarity
    int polarity = eTactile.stimulation_polarity;
    String polarityText = (polarity == 1) ? "Anodic" : "Cathodic";
    parent.text("Polarity: " + polarityText, viewportWidth+50, 580);
    
    viewport.beginDraw();
    viewport.background(0);
    viewport.pushMatrix();
    viewport.translate((viewportWidth / 2) + positionX, (height / 2) + positionY);
    viewport.scale(zoom);
    viewport.rotateX(angleX);
    viewport.rotateY(angleY);
    viewport.fill(100);
    
    graphicsManager.visualize3DObject();
    graphicsManager.drawElectrodes();
    
    graphicsManager.visualizeAndExecute();
    graphicsManager.showPulse();
    graphicsManager.showSensePulse();
    
    //// Display feedback values in the bottom-right corner
    int xPosition = viewportWidth+520;  // Set right-aligned margin
    int yPosition = 550; // Start higher from bottom
    
    parent.textSize(16);
    
    if (disp_elecs_values){
      if (start_elec < 0 || start_elec > dataLoader.electrodes_number-1 || end_elec < 0 || end_elec > dataLoader.electrodes_number-1){
        uiManager.outOfRangeError();
        disp_elecs_values  = false;
      }
      
      else if ((end_elec - start_elec) > 15){
        uiManager.maxRangeError();
        disp_elecs_values  = false;
      }
      
      else if ((end_elec-start_elec) <= 0){
        uiManager.invalidRangeError();
        disp_elecs_values  = false;
      }
      
      else{
        for (int i = 0; i <= end_elec - start_elec; i++) {
          parent.text("Electrode " + (end_elec - i) + ": " + eTactile.voltages[(end_elec - i)], xPosition, yPosition);
          yPosition -= 20;
      }
    }
    
    }
    
    viewport.popMatrix();
    viewport.endDraw();
    image(viewport, 0, 0);
  }
  
  void drawPage2(){
    
    parent.textSize(20);
    parent.fill(255);
    parent.textAlign(PApplet.LEFT);
    parent.text("Tactile Calibration Setup", 43, 100);
    
    parent.textSize(15);
    parent.text("Height: " + lower_thresh_hight , viewportWidth+65, 525);
    parent.text("Width: " + lower_thresh_width , viewportWidth+65, 545);
    
    parent.text("Height: " + upper_thresh_hight , viewportWidth+315, 525);
    parent.text("Width: " + upper_thresh_width , viewportWidth+315, 545);
    
    int imgWidth = 881; 
    int imgHeight = 148; 
    float n = 0.4;
    parent.image(img, viewportWidth+80, 90, n*imgWidth, n*imgHeight);
    
  }
  
  void drawPage4(){
    parent.textSize(20);
    parent.fill(255);
    parent.textAlign(PApplet.LEFT);
    parent.text("Click and Sense program", 43, 100);
    
    int imgWidth = 881; 
    int imgHeight = 148; 
    float n = 0.4;
    parent.image(img, viewportWidth+80, 90, n*imgWidth, n*imgHeight);
    
  }

  void hidePage1UI() {
    cp5.getController("COMPort").hide();
    cp5.getController("browseArrayPattern").hide();
    cp5.getController("initiateETactile").hide();
    cp5.getController("initiateCalibration").hide();
    cp5.getController("initiateClickNSense").hide();
    cp5.getController("browse3DObject").hide();
    cp5.getController("refreshComPort").hide();
  }
  
  void hidePage2UI() {
    cp5.getController("setLowerTreshold").hide();
    cp5.getController("setUpperTreshold").hide();
    cp5.getController("initiateETactile_2").hide();
    cp5.getController("backToPage1_2").hide();
  }
  
  void hidePage3UI() {
    cp5.getController("browseStimulationPattern").hide();
    cp5.getController("startStop").hide();
    cp5.getController("backToPage1").hide();
    cp5.getController("stimulationFrequency").hide();
    cp5.getController("polarityToggle").hide();
    cp5.getController("channelDischargeTime").hide();
    cp5.getController("sensePulseHeight").hide();
    cp5.getController("sensePulseWidth").hide();
    cp5.getController("elec_start").hide();
    cp5.getController("elec_end").hide();
    cp5.getController("Display").hide();
    cp5.getController("toggleOverrideButton").hide();
  }
  
  void hidePage4UI() {
    cp5.getController("initiateETactile_3").hide();
    cp5.getController("backToPage1_4").hide();
  }

  void setupPage3UI() {
    
    img = parent.loadImage("Image/Logo.png"); 
    
    // Button to browse for Stimulation Pattern
    cp5.addButton("browseStimulationPattern")
       .setLabel("Import Pattern JSON")
       .setPosition(viewportWidth+50, 460)
       .setSize(200, 50)
       .setColorForeground(parent.color(60, 179, 113))
       .setColorBackground(parent.color(34, 139, 34))
       .setColorActive(parent.color(50, 205, 50))
       .onClick(event -> {
           String filePath = browseFile("Select Stimulation Pattern", sketchPath("")+"/JSON_Files/patterns");
           if (filePath != null) {
               selectedStimulationPattern = filePath;
               println("Selected Stimulation Pattern: " + selectedStimulationPattern);
               pattern = new File(filePath).getName();
               
               // Update the button label to show the selected file name
               cp5.getController("browseStimulationPattern").setLabel(pattern);
           }
       });
    
    // Start/Stop Button
    cp5.addButton("startStop")
       .setLabel("Start")
       .setPosition(viewportWidth+300, 250)
       .setSize(140, 50)
       .setColorForeground(parent.color(255, 99, 71))
       .setColorBackground(parent.color(255, 69, 0))
       .setColorActive(parent.color(255, 140, 0))
       .onClick(event -> toggleStartStop());

    // Back Button
    cp5.addButton("backToPage1")
       .setLabel("Back to home")
       .setPosition(viewportWidth+50, 250)
       .setSize(140, 50)
       .setColorForeground(parent.color(70, 130, 180))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(100, 149, 237))
       .onClick(event -> {
         currentPage = 1; // Set back to Page 1
         hidePage3UI();
         isRunning = true;
         disp_elecs_values = false;
         show_numbers = false;
         toggleStartStop();
         resetToPage1();  // Reset the UI elements
         local_timer = 0;
       });
     
     
     overrideButton = cp5.addButton("toggleOverrideButton")
        .setLabel("Override")
        .setPosition(viewportWidth+150, 600)
        .setSize(50, 20)
        .onClick(event -> toggleOverride()); // Call function on click
        
     
       
     frequencySlider = cp5.addSlider("stimulationFrequency")
        .setLabel("Stimulation Frequency (Hz)") // Set the label for the slider
        .setPosition(viewportWidth+50, 650)                   // Set the position of the slider
        .setSize(200, 20)                       // Set the size of the slider (unchanged)
        .setRange(5, 200)                       // Set the minimum (5 Hz) and maximum (200 Hz) values
        .setValue(75)                           // Set the default value to 50 Hz
        //.setNumberOfTickMarks(196)              // Set the number of tick marks for granular control
        .setDecimalPrecision(0)                 // Ensure only integer values are displayed
        .setColorForeground(color(255))         // Set the slider handle (thumb) color to white
        .setColorBackground(color(30,144,255))         // Set the background color of the slider bar (track)
        .setColorActive(color(255))             // Set the active color (when interacting) to white
        .setColorValue(color(0, 0))             // Make the filled portion transparent (alpha = 0)
        .setSliderMode(Slider.FLEXIBLE)         // Ensure the handle moves smoothly
        .onChange(event -> {
            // Round the slider value to the nearest integer
            int frequency = Math.round(event.getController().getValue());
            
            // Print the selected frequency to the console
            println("Stimulation Frequency: " + frequency + " Hz");
            
            // Update the stimulation frequency in your application
            updateStimulationFrequency(frequency);
        });
    
    stimModeToggle = cp5.addToggle("polarityToggle")
       .setLabel("Polarity (Anodic/Cathodic)")
       .setPosition(viewportWidth+50, 600)  // Adjust the position as needed
       .setSize(50, 20)       // Larger size for better visibility
       .setValue(true)       // Default state (false = Cathodic, true = Anodic)
       .setMode(ControlP5.SWITCH)  // Set the toggle to behave like a switch
       .setColorForeground(parent.color(60, 179, 113))  // Color when active (Anodic)
       .setColorBackground(parent.color(30,144,255))   // Color when inactive (Cathodic)
       .setColorActive(parent.color(255))       // Color when clicked
       .setColorCaptionLabel(parent.color(255))         // White text for the label
       .setCaptionLabel("Polarity: Anodic")           // Default label text
       .onChange(event -> {
           boolean isAnodic = event.getController().getValue() > 0;
           updatePolarity(isAnodic);  // Call a method to handle polarity change
           // Update the label based on the toggle state
           if (isAnodic) {
               cp5.getController("polarityToggle").setCaptionLabel("Polarity: Anodic");
           } else {
               cp5.getController("polarityToggle").setCaptionLabel("Polarity: Cathodic");
           }
       });
      
      cp5.addSlider("channelDischargeTime")
        .setLabel("Discharge time (ms)") // Set the label for the slider
        .setPosition(viewportWidth+50, 680)                   // Set the position of the slider
        .setSize(200, 20)                       // Set the size of the slider (unchanged)
        .setRange(10, 200)                       // Set the minimum (5 Hz) and maximum (200 Hz) values
        .setValue(50)                           // Set the default value to 50 Hz
        //.setNumberOfTickMarks(196)              // Set the number of tick marks for granular control
        .setDecimalPrecision(0)                 // Ensure only integer values are displayed
        .setColorForeground(color(255))         // Set the slider handle (thumb) color to white
        .setColorBackground(color(30,144,255))         // Set the background color of the slider bar (track)
        .setColorActive(color(255))             // Set the active color (when interacting) to white
        .setColorValue(color(0, 0))             // Make the filled portion transparent (alpha = 0)
        .setSliderMode(Slider.FLEXIBLE)         // Ensure the handle moves smoothly
        .onChange(event -> {
            // Round the slider value to the nearest integer
            int discharge_time = Math.round(event.getController().getValue());
            
            // Print the selected frequency to the console
            println("Stimulation Frequency: " + discharge_time + " ms");
            
            // Update the stimulation frequency in your application
            updateChannelDischargeTime(discharge_time);
        });
        
       
       // Sense Pulse Height Input (0-50)
        cp5.addTextfield("sensePulseHeight")
           .setLabel("Pulse Height (0-50)")
           .setPosition(viewportWidth+400, 640)
           .setSize(50, 20)
           .setAutoClear(false)  // Keeps value after entering
           .setColorForeground(color(255))
           .setColorBackground(color(30,144,255))
           .setColorActive(color(255))
           .setText("0")  // Default value
           .onChange(event -> {
               int sense_height = parseInt(event.getController().getStringValue());
               if (sense_height < 0) sense_height = 0;
               if (sense_height > 50) sense_height = 50;
               println("Pulse Height: " + sense_height);
               updateSensePulseHeight(sense_height);
           });
        
        // Sense Pulse Width Input (0-200)
        cp5.addTextfield("sensePulseWidth")
           .setLabel("Pulse Width (0-200)")
           .setPosition(viewportWidth+400, 680)
           .setSize(50, 20)
           .setAutoClear(false)
           .setColorForeground(color(255))
           .setColorBackground(color(30,144,255))
           .setColorActive(color(255))
           .setText("0")  // Default value
           .onChange(event -> {
               int sense_width = parseInt(event.getController().getStringValue());
               if (sense_width < 0) sense_width = 0;
               if (sense_width > 200) sense_width = 200;
               println("Pulse Width: " + sense_width);
               updateSensePulseWidth(sense_width);
           });
           
       cp5.addTextfield("elec_start")
           .setLabel("start")
           .setPosition(viewportWidth+510, 600)
           .setSize(20, 20)
           .setAutoClear(false)
           .setColorForeground(color(255))
           .setColorBackground(color(30,144,255))
           .setColorActive(color(255))
           .setText("0")  // Default value
           .onChange(event -> {
                int elec_start = parseInt(event.getController().getStringValue());
                electrodes_start_check(elec_start);
           });
           
        cp5.addTextfield("elec_end")
          .setLabel("end")
          .setPosition(viewportWidth+540, 600)
          .setSize(20, 20)
          .setAutoClear(false)
          .setColorForeground(color(255))
          .setColorBackground(color(30,144,255))
          .setColorActive(color(255))
          .setText("0")  // Default value
          .onChange(event -> {
              int elec_end = parseInt(event.getController().getStringValue());
              electrodes_end_check(elec_end);
          });
          
        cp5.addButton("Display")
       .setLabel("Disp")
       .setPosition(viewportWidth+570, 600)
       .setSize(50, 20)
       .setColorForeground(parent.color(70, 130, 180))
       .setColorBackground(parent.color(30, 144, 255))
       .setColorActive(parent.color(100, 149, 237))
       .onClick(event -> {
         display_elecs_values();
       });
       
       updateOverrideButton();
  }

  void resetToPage1() {
    
    if (!calibration_){
      proceed_et = false;
    }
    allowed = false;
    override = false;
    // Show Page 1 elements
    cp5.getController("COMPort").show();
    cp5.getController("browseArrayPattern").show();
    cp5.getController("initiateETactile").show();
    cp5.getController("initiateCalibration").show();
    cp5.getController("initiateClickNSense").show();
    cp5.getController("browse3DObject").show();
    cp5.getController("refreshComPort").show();
    
  }

  void updateButtonLabel(boolean isRunning) {
    cp5.getController("startStop").setLabel(isRunning ? "Stop" : "Start");
  }
  
    String browseFile(String dialogTitle, String initialDirectory) {
      FileDialog fileDialog = new FileDialog((Frame) null, dialogTitle, FileDialog.LOAD);
      fileDialog.setDirectory(initialDirectory);
      fileDialog.setFilenameFilter((dir, name) -> name.toLowerCase().endsWith(".json"));
      fileDialog.setVisible(true);

      String file = fileDialog.getFile();
      if (file != null) {
          return fileDialog.getDirectory() + file;
      }
      return null;
    }
  
    void showWarningDialog() {
    // Create a group to hold the modal dialog elements
    Group warningDialog = cp5.addGroup("warningDialog")
      .setPosition(width/2 - 150, height/2)
      .setSize(300, 200)
      .setBackgroundColor(color(50))
      .setLabel("Warning")
      .hideBar();
  
    // Add a text label to the dialog
    cp5.addTextlabel("warningText")
      .setText("You are going to initialize before calibration!")
      .setPosition(10, 20)
      .setColorValue(color(255))
      .setGroup(warningDialog);
  
    // Add a "Go Back" button
    cp5.addButton("goBack")
      .setLabel("Go Back")
      .setPosition(20, 80)
      .setSize(120, 40)
      .setColorForeground(color(255, 99, 71))
      .setColorBackground(color(255, 69, 0))
      .setColorActive(color(255, 140, 0))
      .setGroup(warningDialog)
      .onClick(event -> {
        warningDialog.hide(); // Hide the dialog
      });
  
    // Add a "Continue" button
    cp5.addButton("continue")
      .setLabel("Continue")
      .setPosition(160, 80)
      .setSize(120, 40)
      .setColorForeground(color(60, 179, 113))
      .setColorBackground(color(34, 139, 34))
      .setColorActive(color(50, 205, 50))
      .setGroup(warningDialog)
      .onClick(event -> {
        allowed = true;
        proceed_et = true;
        warningDialog.hide(); // Hide the dialog
        initializeETactile(); // Setup the third page UI
      });
  
    // Show the dialog
    warningDialog.show();
  }
  
  void showCalibrationSummaryDialog(float lowerHeight, float lowerWidth, float upperHeight, float upperWidth) {
    // Create a group for the modal dialog elements
    Group calibrationDialog = cp5.addGroup("calibrationDialog")
      .setPosition(width/2 - 150, height/2 - 100)
      .setSize(300, 250)
      .setBackgroundColor(color(50))
      .setLabel("Calibration Summary")
      .hideBar();

    // Add a text label to display the calibration details
    cp5.addTextlabel("calibrationSummary")
      .setText("Calibration Summary:\n" + 
                "\n"+
                "\n"+
               "Lower Threshold -   Height: " + lowerHeight + ",   Width: " + lowerWidth + "\n" + 
               "\n"+
               "Upper Threshold -   Height: " + upperHeight + ",   Width: " + upperWidth)
      .setPosition(10, 20)
      .setColorValue(color(255))
      .setGroup(calibrationDialog);

    // Add a "Go Back" button
    cp5.addButton("goBack")
      .setLabel("Go Back")
      .setPosition(20, 150)
      .setSize(120, 40)
      .setColorForeground(color(255, 99, 71))
      .setColorBackground(color(255, 69, 0))
      .setColorActive(color(255, 140, 0))
      .setGroup(calibrationDialog)
      .onClick(event -> {
        calibrationDialog.hide(); // Hide the dialog
      });

    // Add a "Continue" button
    cp5.addButton("continue")
      .setLabel("Continue")
      .setPosition(160, 150)
      .setSize(120, 40)
      .setColorForeground(color(60, 179, 113))
      .setColorBackground(color(34, 139, 34))
      .setColorActive(color(50, 205, 50))
      .setGroup(calibrationDialog)
      .onClick(event -> {
        proceed_et = true;
        confirm = true;
        allowed =false;
        calibrationDialog.hide(); // Hide the dialog
        initializeETactile(); // Proceed to the next stage
      });

    // Show the dialog
    calibrationDialog.show();
}
  
  // Method to update the stimulation frequency
  void updateStimulationFrequency(int frequency) {
      // Implement the logic to update the stimulation frequency in your system
      eTactile.send_stimulation_frequency(frequency);
      println("Updated Stimulation Frequency to: " + frequency + " Hz");
  }
  
  // Method to update the stimulation frequency
  void updateChannelDischargeTime(int discharge_time) {
      // Implement the logic to update the stimulation frequency in your system
      eTactile.send_channel_discharge_time(discharge_time);
      println("Updated channel discharge time to: " + discharge_time + " ms");
  }
  
  // Method to update the stimulation frequency
  void updateSensePulseHeight(int sense_height) {
      // Implement the logic to update the stimulation frequency in your system
      eTactile.send_sense_pulse_height(sense_height);
      println("Updated sense pulse height to: " + sense_height);
  }
  
  // Method to update the stimulation frequency
  void updateSensePulseWidth(int sense_width) {
      // Implement the logic to update the stimulation frequency in your system
      eTactile.send_sense_pulse_width(sense_width);
      println("Updated sense pulse height to: " + sense_width);
  }
  
  
  void updatePolarity(boolean isAnodic) {
    if (isAnodic) {
        println("Polarity set to Anodic");
        eTactile.send_stimulation_polarity(1);
        // Implement logic to set polarity to anodic
      } else {
        eTactile.send_stimulation_polarity(0);
          println("Polarity set to Cathodic");
          // Implement logic to set polarity to cathodic
      }
  }
  
  void showExceedWarningDialog(float currentHeight, float currentWidth, float maxHeight, float maxWidth) {
    // Create a group for the warning dialog
    Group exceedWarningDialog = cp5.addGroup("exceedWarningDialog")
      .setPosition(width/2 - 150, height/2 - 100)
      .setSize(300, 200)
      .setBackgroundColor(color(50))
      .setLabel("Warning: Limits Exceeded")
      .hideBar();

    // Add a text label to display the exceeded values
    cp5.addTextlabel("exceedWarningText")
      .setText("Warning! Exceeded Calibration Limits!\n" + "\n" + "\n"+
               "Current - H: " + currentHeight + ", W: " + currentWidth + "\n" + "\n" +
               "Allowed - H: " + maxHeight + ", W: " + maxWidth)
      .setPosition(10, 20)
      .setColorValue(color(255))
      .setGroup(exceedWarningDialog);

    // Add a "Go Back" button to stay on the current stage
    cp5.addButton("exceedGoBack")
      .setLabel("Go Back")
      .setPosition(165, 120)
      .setSize(120, 40)
      .setColorForeground(color(255, 99, 71))
      .setColorBackground(color(255, 69, 0))
      .setColorActive(color(255, 140, 0))
      .setGroup(exceedWarningDialog)
      .onClick(event -> {
        exceedWarningDialog.hide(); // Hide the dialog
      });
    
    cp5.addButton("continue")
      .setLabel("Continue")
      .setPosition(15, 120)
      .setSize(120, 40)
      .setColorForeground(color(60, 179, 113))
      .setColorBackground(color(34, 139, 34))
      .setColorActive(color(50, 205, 50))
      .setGroup(exceedWarningDialog)
      .onClick(event -> {
        exceedWarningDialog.hide();
        allowed = true;
      });


      // Show the dialog
      exceedWarningDialog.show();
  }
  
  void drawViewportPage(){
    viewport.beginDraw();
    viewport.background(0);
    viewport.pushMatrix();
    viewport.translate(viewportWidth / 2 + 50, height / 2);
    viewport.scale(zoom);
    
    // Slowly rotate the logo
    viewport.rotateY(angleY);

    viewport.imageMode(CENTER);
    viewport.image(logo, 0, 0, logo.width * 0.6, logo.height * 0.6);

    viewport.popMatrix();
    viewport.endDraw();
    image(viewport, 0, 0);

    // Increment rotation angles for smooth rotation
    angleY += 0.01;
  }
  
  void showArrayInitializationErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("initializationErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Initialization Failed")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("initializationErrorText")
      .setText("Please select an Array JSON file\nbefore initializing.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showObjInitializationErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("initializationErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Initialization Failed")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("initializationErrorText")
      .setText("Please select an Object file\nbefore initializing.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showInitializationErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("initializationErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Initialization Failed")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("initializationErrorText")
      .setText("Please select Array & Object files\nbefore initializing.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showPatternInitializationErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("initializationErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Initialization Failed")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("initializationErrorText")
      .setText("Please select a Pattern JSON file\nbefore initializing.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showArrayFileErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("fileErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Invalid File")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("fileErrorText")
      .setText("Invalid Array JSON files.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showPatternFileErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("fileErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Invalid File")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("fileErrorText")
      .setText("Invalid Pattern JSON file \nPlease select a valid pattern files.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);
      
    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showElectrodeMissMatchErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("misMatchErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Electrode Mismatch")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("fileErrorText")
      .setText("Electrode number miss match between \nArray file & Pattern file.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);
      
    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void showObjectErrorDialog() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("objectErrorDialog")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Invalid Object")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("objectErrorText")
      .setText("Invalid object file.")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void outOfRangeError() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("outOfRange")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: Out of range")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("fileErrorText")
      .setText("Electrode number is \nout of range")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void maxRangeError() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("maxRange")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: max range")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("fileErrorText")
      .setText("Maximum range is 16")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void invalidRangeError() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("invalidRange")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: invalid range")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("fileErrorText")
      .setText("Invalid Range")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

void invalidComPortError() {
    // Create a group for the warning dialog
    Group initializationErrorDialog = cp5.addGroup("invalidComPort")
      .setPosition(width/2 - 150, 500)
      .setSize(300, 150)
      .setBackgroundColor(color(50))
      .setLabel("Error: invalid COM port")
      .hideBar();

    // Add a text label to display the error message
    cp5.addTextlabel("Comport ErrorText")
      .setText("Invalid COM Port selection.\nPlease Refresh!")
      .setPosition(40, 40)
      .setColorValue(color(255))
      .setGroup(initializationErrorDialog);

    // Add an "OK" button to close the dialog
    cp5.addButton("okButton")
      .setLabel("OK")
      .setPosition(90, 90)
      .setSize(120, 40)
      .setColorForeground(color(200, 200, 200))
      .setColorBackground(color(100, 100, 100))
      .setColorActive(color(150, 150, 150))
      .setGroup(initializationErrorDialog)
      .onClick(event -> {
        initializationErrorDialog.hide(); // Hide the dialog
      });

    // Show the dialog
    initializationErrorDialog.show();
}

// Function to update button colors based on override state
void updateOverrideButton() {
    if (override) {
        overrideButton
            .setColorForeground(parent.color(50, 205, 50))  // Green (override = true)
            .setColorBackground(parent.color(34, 139, 34))
            .setColorActive(parent.color(0, 128, 0));
         stimModeToggle
             .setColorForeground(parent.color(60, 179, 113))  // Color when active (Anodic)
             .setColorBackground(parent.color(30,144,255))   // Color when inactive (Cathodic)
             .setColorActive(parent.color(255))       // Color when clicked
             .setLock(false);
         frequencySlider
             .setColorForeground(color(255))     
             .setColorBackground(color(30,144,255)) 
             .setColorActive(color(255)) 
             .setLock(false);
    } else {
        overrideButton
            .setColorForeground(parent.color(255, 99, 71))  // Red-Orange (override = false)
            .setColorBackground(parent.color(255, 69, 0))
            .setColorActive(parent.color(255, 140, 0));
        stimModeToggle
             .setColorForeground(parent.color(60, 179, 113))  // Color when active (Anodic)
             .setColorBackground(parent.color(30,144,200))   // Color when inactive (Cathodic)
             .setColorActive(parent.color(200))       // Color when clicked
             .setLock(true);
           
         frequencySlider
             .setColorForeground(color(200))     
             .setColorBackground(color(30,144,200)) 
             .setColorActive(color(200)) 
             .setLock(true);
            
    }
}
  
}
