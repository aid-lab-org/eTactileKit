ETactile eTactile;

String electrodes_locs = "JSON_Files/coordinates.json"; 
String object3D = "Objects/StanfordBunny.obj";        

String output_name = "Created_patterns/created_new_pattern_3D";

// Variables for the plane pattern generation
float startX = -72;    // X-coordinate of the plane's starting position
float startY = -60;    // Y-coordinate of the plane's starting position
float startZ = 20;     // Z-coordinate of the plane's starting position
int plane_width = 100;      // Width of the plane
int plane_length = 100;     // Length of the plane
int plane_height = 1;       // Thickness of the plane
int increment = 1;
int delay_time = 200;
int terminating_cond = 55;
float currentZ = startZ;

void setup() {
  size(1000, 900, P3D);
  eTactile = new ETactile(this);
  eTactile.setIsInsideShape3D(this::isInsideShape);
  eTactile.setup3D(electrodes_locs, object3D, output_name);  
}

void draw() {
  
  fill(0, 255, 0, 100); // Use semi-transparent green for the plane
  // Draw the moving plane
  pushMatrix();
  translate(startX + plane_width / 2, startY + plane_length / 2, currentZ + plane_height / 2);
  box(plane_width, plane_length, plane_height); // Draw the plane as a thin box
  popMatrix();
  
  eTactile.eTframedelay(delay_time);
  
  currentZ += increment;
  
  if (currentZ >= terminating_cond){
    eTactile.terminate();
    currentZ = startZ;
  } 
}

boolean isInsideShape(float x, float y, float z) {
  
  boolean withinX = x >= startX && x <= (startX + plane_width);
  boolean withinY = y >= startY && y <= (startY + plane_length);
  boolean withinZ = z >= currentZ && z <= (currentZ + plane_height);

  return withinX && withinY && withinZ;
  
}
