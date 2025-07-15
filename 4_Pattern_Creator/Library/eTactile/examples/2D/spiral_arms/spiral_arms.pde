import eTactile.*;

ETactile eTactile;

String electrode_board_file = "Data/electrode_array_main_board.json";
String output_file = "Data/created_patterns/spiral_arms";

float angle = 0;
float angleStep = PI / 60;
int spinCount = 3;
int maxSpins = 5;

int numArms = 5;
float baseLength = 100;
float pulseRange = 50;
float armWidth = 20;

float cx = 500;  // Center of rotation
float cy = 350;

void setup() {
  size(1000, 900);
  eTactile = new ETactile(this);
  eTactile.setup2D(electrode_board_file, output_file);

}

void draw() {
  
  // Pulse effect using sine wave
  float pulse = baseLength + sin(frameCount * 0.1) * pulseRange;

  for (int i = 0; i < numArms; i++) {
    float a = angle + TWO_PI * i / numArms;

    // Direction vector of arm
    float dx = cos(a);
    float dy = sin(a);

    // Perpendicular vector for width
    float px = -dy;
    float py = dx;

    // Center of arm
    float armCx = cx + dx * pulse / 2;
    float armCy = cy + dy * pulse / 2;

    float hl = pulse / 2;
    float hw = armWidth / 2;

    // Four corners
    float x1 = armCx - dx * hl - px * hw;
    float y1 = armCy - dy * hl - py * hw;

    float x2 = armCx + dx * hl - px * hw;
    float y2 = armCy + dy * hl - py * hw;

    float x3 = armCx + dx * hl + px * hw;
    float y3 = armCy + dy * hl + py * hw;

    float x4 = armCx - dx * hl + px * hw;
    float y4 = armCy - dy * hl + py * hw;

    fill(0, 255, 0, 100);
    noStroke();
    beginShape();
    vertex(x1, y1);
    vertex(x2, y2);
    vertex(x3, y3);
    vertex(x4, y4);
    endShape(CLOSE);
  }

  angle += angleStep;
  
  eTactile.eTfreq(75);
  eTactile.eTmode("Anodic");
  eTactile.eTframedelay(50);

  if (angle >= TWO_PI) {
    angle -= TWO_PI;
    spinCount++;
    if (spinCount >= maxSpins) {
      eTactile.terminate();
      spinCount = 0;
    }
  }
}
