import eTactile.*;
import peasy.*;

ETactile eTactile;

String electrodes_locs   = "Data/coordinates.json";              // Path to the electrode coordinates
String object3D          = "Data/StanfordBunny.obj";             // Path to the 3D object        

String output_name = "Data/created_patterns/output_file_name";   // Path to the output JSON file

// Definr your pattern variables here

void setup() {
  size(1000, 900, P3D);
  eTactile = new ETactile(this);
  eTactile.setIsInsideShape3D(this::isInsideShape);
  eTactile.setup3D(electrodes_locs, object3D, output_name);  
}

void draw() {
  
  // Define your pattern in here
  
}

boolean isInsideShape(float x, float y, float z) {
  
  // Define your inclusion criteria here
  // Overlap in 3D space
  
  return false;
  
}
