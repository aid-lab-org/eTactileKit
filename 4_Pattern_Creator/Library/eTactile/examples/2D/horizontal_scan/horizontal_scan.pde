import eTactile.*;

ETactile eTactile; 

String electrode_board_file = "Data/electrode_array_main_board.json";            // JSON file with electrode data
String output_file          = "Data/created_patterns/horizontal_scan";           // Name of the output JSON file

// Pattern variables
float startX = 320; 
float endX = 670;               //(startX - endX = length of the line)

float startY = 200;
float currentY = startY;

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
  
  line(startX, currentY, endX, currentY);
  currentY += increment;
  
  eTactile.eTfreq(75);           // Stimulation frequency
  eTactile.eTmode("Anodic");     // Stimulation mode
  
  eTactile.eTframedelay(10);     // Delay between frames (ms)
  
  if (currentY >= 500) {
    currentY = startY;           // Starting point (for repeating)
    eTactile.terminate();        // Save pattern and exit sketch
  }
}
