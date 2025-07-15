import eTactile.*;
import peasy.*;

ETactile eTactile;

String electrodes_locs = "Data/coordinates.json"; 
String object3D = "Data/StanfordBunny.obj";        
String output_name = "Data/created_patterns/rotating_plane";

// Plane parameters
float planeSize = 50;  // Size of the square plane
float planeAngle = 0;   // Current rotation angle (in radians)
float rotationSpeed = 0.05; // Speed of rotation (radians per frame)
float planeThickness = 2;  // How thick the plane is (for activation)

// Plane position (centered near your electrode array)
float centerX = -35;  
float centerY = -29;
float centerZ = 50;

void setup() {
  size(1000, 900, P3D);
  eTactile = new ETactile(this);
  eTactile.setIsInsideShape3D(this::isInsideRotatingPlane);
  eTactile.setup3D(electrodes_locs, object3D, output_name);  
}

void draw() {
  background(0);
  
  // Visualize the rotating plane (for debugging)
  pushMatrix();
  translate(centerX, centerY, centerZ);
  rotateY(planeAngle);
  fill(0, 255, 0, 100);
  box(planeSize, planeSize, planeThickness);
  popMatrix();
  
  eTactile.eTfreq(75);
  eTactile.eTmode("Anodic");
  
  eTactile.eTframedelay(50);
  
  // Update plane rotation
  planeAngle += rotationSpeed;
  
  // Reset after full rotation
  if (planeAngle > TWO_PI) {
    planeAngle = 0;
    eTactile.terminate();
  }
}

boolean isInsideRotatingPlane(float x, float y, float z) {
  // Transform point to plane's coordinate system
  float relX = x - centerX;
  float relY = y - centerY;
  float relZ = z - centerZ;
  
  // Rotate point backwards to check against axis-aligned plane
  float rotatedX = relX * cos(-planeAngle) - relZ * sin(-planeAngle);
  float rotatedZ = relX * sin(-planeAngle) + relZ * cos(-planeAngle);
  
  // Check if point is within the plane's dimensions
  boolean inPlaneX = abs(rotatedX) < planeSize/2;
  boolean inPlaneY = abs(relY) < planeSize/2;
  boolean inPlaneZ = abs(rotatedZ) < planeThickness/2;
  
  return inPlaneX && inPlaneY && inPlaneZ;
}
