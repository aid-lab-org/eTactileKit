import eTactile.*;

ETactile eTactile; 

String electrode_board_file = "Data/electrode_array_main_board.json";            // JSON file with electrode data
String output_file          = "Data/created_patterns/fading_horizontal_scan";    // Name of the output JSON file

// Pattern variables
float startX = 320; 
float endX = 670;               //(startX - endX = length of the line)

float startY = 200;
float currentY = startY;

int increment = 1;
int stroke_width = 15;

float fadeSpeed = 0.5;           // Slower fading speed
int currentAlpha = 255;          // Initial alpha (fully visible)
int minAlpha = 20;               // Minimum alpha value

float minFreq = 50;              // Minimum frequency
float maxFreq = 120;             // Maximum frequency
float currentFreq = minFreq;     // Starting frequency

void setup() {
  size(1000, 900);
  
  eTactile = new ETactile(this);                     
  eTactile.setup2D(electrode_board_file, output_file);
}

void draw() {
  // Calculate the progress of the line drawing based on currentY
  float progress = (currentY - startY) / (500 - startY);  // Normalized progress (0 to 1)

  // Linearly decrease the alpha value (255 to 20) as the progress goes from 0 to 1
  currentAlpha = (int) lerp(255, minAlpha, progress);
  
  // Linearly increase the frequency (50 to 120) as the progress goes from 0 to 1
  currentFreq = lerp(minFreq, maxFreq, progress);
  
  // Apply the fading effect to the stroke
  stroke(0, 255, 0, currentAlpha);  // Green color with fading alpha
  strokeWeight(stroke_width);
  noFill();
  
  line(startX, currentY, endX, currentY);
  currentY += increment;
  
  // Update eTactile with the current frequency
  eTactile.eTfreq(int(currentFreq));           // Stimulation frequency (smoothly transitioning)
  eTactile.eTmode("Anodic");             // Stimulation mode
  eTactile.eTframedelay(10);             // Delay between frames (ms)
  
  if (currentY >= 500) {
    currentY = startY;           // Starting point (for repeating)
    currentAlpha = 255;
    eTactile.terminate();         // Save pattern and exit sketch
  }
}
