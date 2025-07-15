import eTactile.*;

ETactile eTactile;

String electrode_board_file = "Data/electrode_array_main_board.json";                   // JSON file with electrode data
String output_file          = "Data/created_patterns/select_and_activate";                 // Name of the output JSON file

int blinkInterval = 500;     // Interval between blinks (ms)
int lastBlinkTime = 0;
boolean isOn = false;
int blinkCount = 0;
int maxBlinks = 10;

void setup() {
  size(1000, 900);

  eTactile = new ETactile(this);
  eTactile.setup2D(electrode_board_file, output_file);

}

void draw() {
  if (millis() - lastBlinkTime >= blinkInterval) {
    isOn = !isOn;             // Toggle ON/OFF
    lastBlinkTime = millis();
    blinkCount++;
  }

  if (isOn) {
    fill(0, 128, 255, 100);   // Semi-transparent blue
    noStroke();
    rectMode(CENTER);

    // Draw four small rectangles (spread across the canvas)
    rect(450, 250, 50, 50);  // Top-left rectangle
    rect(400, 350, 50, 50);  // Top-right rectangle
    rect(600, 350, 50, 50);  // Bottom-left rectangle
    rect(500, 450, 50, 50);  // Bottom-right rectangle
  } 
  
  eTactile.eTfreq(75);            // Stimulation frequency
  eTactile.eTmode("Anodic");      // Stimulation mode
  eTactile.eTframedelay(blinkInterval);  // Delay between frames

  if (blinkCount >= maxBlinks) { // Each blink has on and off
    blinkCount = 0;          // Reset blink count (for repeating)
    eTactile.terminate();    // Save pattern and exit
  }
}
