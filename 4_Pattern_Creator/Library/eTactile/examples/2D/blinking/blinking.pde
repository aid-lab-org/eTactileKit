import eTactile.*;

ETactile eTactile;

String electrode_board_file = "Data/electrode_array_main_board.json";                   // JSON file with electrode data
String output_file          = "Data/created_patterns/blinking_pattern";                 // Name of the output JSON file

int blinkInterval = 500;     // Interval between blinks (ms)
int lastBlinkTime = 0;
boolean isOn = false;
int blinkCount = 0;
int maxBlinks = 10;

void setup() {
  size(1000, 900);

  eTactile = new ETactile(this);
  eTactile.setup2D(electrode_board_file, output_file);

  eTactile.eTfreq(75);            // Stimulation frequency
  eTactile.eTmode("Anodic");      // Stimulation mode
  eTactile.eTframedelay(blinkInterval);  // Delay between frames
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
    rect(500, 350, 300, 300);  // Draw blinking rectangle  (centered on electrode board)
  }

  if (blinkCount >= maxBlinks) { // Each blink has on and off
    blinkCount = 0;          // Reset blink count (for repeating)
    eTactile.terminate();    // Save pattern and exit
  }
}
