import eTactile.*;

ETactile eTactile; 

String electrode_board_file = "Data/electrode_array_main_board.json";              // Path to the JSON file with electrode data
String output_file          = "Data/created_patterns/output_file_name";            // Path to the output JSON file

// Definr your pattern variables here

void setup() {
  size(1000, 900);
  
  eTactile = new ETactile(this);                     
  eTactile.setup2D(electrode_board_file, output_file);
}

void draw() {
  // Define your graphical pattern in here
}
