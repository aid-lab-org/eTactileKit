import eTactile.*;
import peasy.*;

ETactile eTactile;

String electrodes_locs = "Data/coordinates.json"; 
String object3D = "Data/StanfordBunny.obj";    

String output_name = "Data/created_patterns/expanding_sphere";

// Sphere pulse pattern
float pulseRadius = 1;
float pulseIncrement = 0.5;
float minRadius = 1;
float maxRadius = 6;

int delay_time = 200;
boolean pattern_saved = false;

PVector pulseCenter = new PVector(-36, -29, 50); // Center near electrode cluster

void setup() {
  size(1000, 900, P3D);
  eTactile = new ETactile(this);
  eTactile.setIsInsideShape3D(this::isInsideShape);
  eTactile.setup3D(electrodes_locs, object3D, output_name);  
}

void draw() {
  background(0);
  lights();

  // Draw the pulsing sphere
  pushMatrix();
  translate(pulseCenter.x, pulseCenter.y, pulseCenter.z);
  noFill();
  stroke(255, 0, 0);
  sphere(pulseRadius);
  popMatrix();
  
  eTactile.eTfreq(75);
  eTactile.eTmode("Anodic");
  
  eTactile.eTframedelay(delay_time);

  // Update radius
  pulseRadius += pulseIncrement;
  if (pulseRadius >= maxRadius || pulseRadius <= minRadius) {
    pulseIncrement *= -1; // Reverse the pulse
  }
  
  if (pulseRadius == 1 && !pattern_saved){  //pulseRadius is back to 1 after a one cycle completed.
    eTactile.terminate();
    pattern_saved = true;
  }
}

boolean isInsideShape(float x, float y, float z) {
  float distance = dist(x, y, z, pulseCenter.x, pulseCenter.y, pulseCenter.z);
  return distance <= pulseRadius;
}
