import eTactile.*;

ETactile eTactile; 

String electrode_board_file = "Data/electrode_array_main_board.json";                   // JSON file with electrode data
String output_file          = "Data/created_patterns/diverging_ring_pattern";           // Name of the output JSON file

// Pattern variables
float centerX     = 500;
float centerY     = 350;
int   radius      = 0;
int   stroke_width = 10;

void setup() {
  size(1000, 900);
  
  eTactile = new ETactile(this);                     
  eTactile.setup2D(electrode_board_file, output_file);
}

void draw() {
  stroke(255, 0, 0);   // Required to set color
  strokeWeight(stroke_width);
  noFill();
  
  ellipse(centerX, centerY, radius * 2, radius * 2); // Draw expanding ring
  radius += 5;

  eTactile.eTfreq(75);           // Stimulation frequency
  eTactile.eTmode("Anodic");     // Stimulation mode
  
  eTactile.eTframedelay(100);    // Delay between frames (ms)

  if (radius >= 180) {
    radius = 5;                  // Initial radius (for repeating)
    eTactile.terminate();        // Save pattern and exit sketch
  }
}
