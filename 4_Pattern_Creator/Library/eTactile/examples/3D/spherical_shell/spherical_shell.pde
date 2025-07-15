import eTactile.*;
import peasy.*;

ETactile eTactile;

String electrodes_locs = "Data/coordinates.json"; 
String object3D = "Data/StanfordBunny.obj";        
String output_name = "Data/created_patterns/created_expanding_shell";

float centerX = -20;
float centerY = -20;
float centerZ = 25;

float currentRadius = 0;
float shellThickness = 4;       // Thickness of the shell
float radiusIncrement = 1.5;    // Speed of expansion
float maxRadius = 40;

int delay_time = 200;

void setup() {
  size(1000, 900, P3D);
  eTactile = new ETactile(this);
  eTactile.setIsInsideShape3D(this::isInsideShape);
  eTactile.setup3D(electrodes_locs, object3D, output_name);
  
}

void draw() {
  background(0);
  lights();
  
  noFill();
  stroke(0, 200, 255, 150);  // Cyan glow for shell
  strokeWeight(1.5);
  
  pushMatrix();
  translate(centerX, centerY, centerZ);
  sphere(currentRadius + shellThickness / 2);  // Visualization only
  popMatrix();
  
  eTactile.eTfreq(75);
  eTactile.eTmode("Anodic");
  
  eTactile.eTframedelay(delay_time);
  
  currentRadius += radiusIncrement;
  
  if (currentRadius >= maxRadius) {
    eTactile.terminate();
    currentRadius = 0;
  }
}

boolean isInsideShape(float x, float y, float z) {
  float dx = x - centerX;
  float dy = y - centerY;
  float dz = z - centerZ;
  
  float dist = sqrt(dx * dx + dy * dy + dz * dz);
  return dist >= currentRadius && dist <= (currentRadius + shellThickness);
}
