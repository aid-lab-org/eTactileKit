import controlP5.*;

PImage logo;
ControlP5 cp5;

void setup() {
  size(1000, 900);
  cp5 = new ControlP5(this);
  logo = loadImage("Logo/logo.png"); // Ensure "logo.png" is in the data folder
  
  // Create buttons using CP5
  cp5.addButton("launch2D")
     .setLabel("2D Mode")
     .setPosition(310, 600)
     .setSize(140, 60)
     .setColorBackground(color(0, 100, 255))
     .setColorForeground(color(0, 150, 255))
     .setColorActive(color(0, 180, 255))
     .setColorLabel(color(255));

  cp5.addButton("launch3D")
     .setLabel("3D Mode")
     .setPosition(550, 600)
     .setSize(140, 60)
     .setColorBackground(color(255, 80, 0))
     .setColorForeground(color(255, 120, 50))
     .setColorActive(color(255, 160, 100))
     .setColorLabel(color(255));
}

void draw() {
  drawGradientBackground(); // Custom gradient background
  
  // Draw the logo
  imageMode(CENTER);
  image(logo, width / 2, 250, logo.width * 0.7, logo.height * 0.7);

  // Title text
  fill(255);
  textSize(40);
  textAlign(CENTER, CENTER);
  text("Welcome to eTactileKit", width / 2, 450);
}

// Gradient background (black to blue)
void drawGradientBackground() {
  for (int i = 0; i < height; i++) {
    float inter = map(i, 0, height, 0, 1);
    color c = lerpColor(color(0, 0, 0), color(0, 50, 150), inter);
    stroke(c);
    line(0, i, width, i);
  }
}

// Button actions
void launch2D() {
  launchSketch("2D/Main");
}

void launch3D() {
  launchSketch("3D/Main");
}

void launchSketch(String sketchFolder) {
  try {
    String sketchPath = sketchPath(sketchFolder);
    Runtime.getRuntime().exec(new String[]{"processing-java", "--sketch=" + sketchPath, "--run"});
    delay(1000);
    exit();
  } catch (Exception e) {
    e.printStackTrace();
  }
}
