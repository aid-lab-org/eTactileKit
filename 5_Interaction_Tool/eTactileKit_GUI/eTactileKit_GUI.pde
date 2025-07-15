import controlP5.*;

PImage logo;
ControlP5 cp5;

void setup() {
  size(1000, 900);
  surface.setLocation(100,100);
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
    String skPath = sketchPath(sketchFolder);
    String osName = System.getProperty("os.name").toLowerCase();
    if (osName.contains("windows")) {
      // Windows: Always run 'processing-java' from the default installation path of Processing
      runProcessingJava("processing-java", skPath);

    } else if (osName.contains("mac")) {
      // macOS: Users had trouble running 'processing-java' from the default installation path of Processing
      // So, we use the full path to the 'processing-java' executable
      runProcessingJava("/usr/local/bin/processing-java", skPath);

    } else {
      println("Unsupported OS");
    }
    delay(1000);
    exit();
  } catch (Exception e) {
    e.printStackTrace();
  }
}

/**
 * Spawns a new Process using the given processing-java path and sketch path.
 */
void runProcessingJava(String processingCommand, String sketchPath) throws IOException {
  String[] cmd = { processingCommand, "--sketch=" + sketchPath, "--run" };
  Runtime.getRuntime().exec(cmd);
}
