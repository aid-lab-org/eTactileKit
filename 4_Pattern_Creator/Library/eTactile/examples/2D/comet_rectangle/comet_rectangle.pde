import eTactile.*;

ETactile eTactile;

String electrode_board_file = "Data/electrode_array_main_board.json";
String output_file = "Data/created_patterns/spinning_comet_pattern";

float angle = 0;
float angleStep = PI / 30;     // Rotation step per frame
int spinCount = 0;
int maxSpins = 5;
float cometLength = 150;
float cometWidth = 20;

void setup() {
  size(1000, 900);
  eTactile = new ETactile(this);
  eTactile.setup2D(electrode_board_file, output_file);

}

void draw() {
  
  //(cx,cy) = rotating center
  float cx = 500;
  float cy = 350;

  // Center of the comet rectangle
  float distFromCenter = cometLength / 2;
  float cometCx = cx + cos(angle) * distFromCenter;
  float cometCy = cy + sin(angle) * distFromCenter;

  // Direction vector
  float dx = cos(angle);
  float dy = sin(angle);

  // Perpendicular vector for width
  float px = -dy;
  float py = dx;

  // Half sizes
  float hl = cometLength / 2;
  float hw = cometWidth / 2;

  // Rectangle corners
  float x1 = cometCx - dx * hl - px * hw;
  float y1 = cometCy - dy * hl - py * hw;

  float x2 = cometCx + dx * hl - px * hw;
  float y2 = cometCy + dy * hl - py * hw;

  float x3 = cometCx + dx * hl + px * hw;
  float y3 = cometCy + dy * hl + py * hw;

  float x4 = cometCx - dx * hl + px * hw;
  float y4 = cometCy - dy * hl + py * hw;

  fill(255, 0, 0, 120); // Semi-transparent red
  noStroke();
  beginShape();
  vertex(x1, y1);
  vertex(x2, y2);
  vertex(x3, y3);
  vertex(x4, y4);
  endShape(CLOSE);

  // Update rotation
  angle += angleStep;
  
  
  eTactile.eTfreq(75);
  eTactile.eTmode("Anodic");
  eTactile.eTframedelay(50);

  // Count full rotations
  if (angle >= TWO_PI) {
    angle -= TWO_PI;
    spinCount++;
    if (spinCount >= maxSpins) {
      spinCount = 0;
      eTactile.terminate();  // Save and end
    }
  }
}
