import eTactile.*;

ETactile eTactile; 

String electrode_board_file = "Data/electrode_array_main_board.json";          // JSON file with electrode data
String output_file          = "Data/created_patterns/vertical_scan";           // Name of the output JSON file

// Pattern variables
float startY = 200; 
float endY = 500;               //(startY - endY = length of the line)

float startX = 350;
float currentX = startX;

int increment = 1;
int stroke_width = 10;

void setup() {
  size(1000, 900);
  
  eTactile = new ETactile(this);                     
  eTactile.setup2D(electrode_board_file, output_file);
}

void draw() {
  stroke(0, 255, 0);  
  strokeWeight(stroke_width);
  noFill();
  
  line(currentX, startY, currentX, endY);
  currentX += increment;
  
  eTactile.eTfreq(75);           // Stimulation frequency
  eTactile.eTmode("Anodic");     // Stimulation mode
  
  eTactile.eTframedelay(10);     // Delay between frames (ms)
  
  if (currentX >= 650) {
    currentX = startX;           // Starting point (for repeating)
    eTactile.terminate();        // Save pattern and exit sketch
  }
}
