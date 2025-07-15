import eTactile.*;            
import gifAnimation.*;        // Import gifAnimation library for handling GIFs

ETactile eTactile;           
Gif myGif;                   // Declare the Gif object to manage GIF animation


String electrode_board_file = "Data/electrodes_64.json";                  // JSON file with electrode data
String gif_file             = "Data/sine_wave.gif";                       // GIF file for displaying animation
String output_file          = "Data/created_patterns/sine_wave_pattern";  // Output JSON file for generated patterns

// Pattern variables
PImage[] frames;            // Array to store frames of the GIF
int frame_count = 0;        // Counter to keep track of the number of frames

void setup() {
  size(1000, 900);          
  
  eTactile = new ETactile(this); 
  myGif = new Gif(this, gif_file); 
  
  
  eTactile.setup2D(electrode_board_file, output_file);
  frames = Gif.getPImages(this, gif_file);
  
  myGif.play(); // Start playing the GIF animation
}

void draw() {
  image(myGif, 230, 180);   // Display the current GIF frame at the specified position
  
  eTactile.eTfreq(75);          // Frequency set to 75 Hz
  eTactile.eTmode("Anodic");    // Mode is set to Anodic
  eTactile.eTframedelay(10);    // 10 milliseconds delay between frames
  
  frame_count ++;             // Increment the frame counter
  
  // Once the number of frames displayed reaches twice the total frame count, terminate the stimulation
  if (frame_count == frames.length * 2){
    eTactile.terminate();
  }
}
