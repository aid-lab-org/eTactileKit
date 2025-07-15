package eTactile;

import processing.core.*;
import processing.data.*;

public class Visualizer {

    

    JSONArray coordinates;
    JSONArray electrodes;
    
    int electrodes_number;
    float[][] electrode_positions; // Store positions
    
    float scaleFactor;
    boolean needToScale = false;

    PApplet parent;
    private ETactile eTactile;
    
    public Visualizer(PApplet parent,ETactile eTactile) {
        this.parent = parent;
        this.eTactile = eTactile;
        this.coordinates = eTactile.coordinates;
        this.electrodes = eTactile.electrodes;
        this.electrodes_number = eTactile.electrodes_number;
        this.electrode_positions = new float[electrodes_number][2]; // Store positions
    }

    void visualizeArrayPattern() {
        parent.fill(0, 0, 255); // blue color for the electrodes
        parent.noStroke();
        
        // Loop through the electrode points and draw each as a circle
        for (int i = 0; i < electrodes.size(); i++) {
        JSONObject electrode = electrodes.getJSONObject(i);
        
        float x,y;
        
        if (needToScale){
            x = ((electrode.getFloat("x") * scaleFactor) * 10 + 500);
            y = (900-((electrode.getFloat("y") * scaleFactor) * 10 + 500));
            eTactile.electrodeSize = 10 * (eTactile.electrodeRadius) * scaleFactor;
        }
        
        else {
            x = (electrode.getFloat("x")*10+500);
            y = (900-(electrode.getFloat("y")*10+500));
            eTactile.electrodeSize = 10 * (eTactile.electrodeRadius);
        }
        
        int number = eTactile.mapping_func[i];
        
        electrode_positions[i][0] = x; // Store x position
        electrode_positions[i][1] = y; // Store y position
        
        if (eTactile.isInsideShape2D(x,y,i)){
            eTactile.elecs_data[i] = 1;
            parent.fill(255,0,0);
        }
        
        else{
            eTactile.elecs_data[i] = 0;
            parent.fill(0,0,255);
        }
        
        // Draw each electrode as a circle
        parent.ellipse(x, y, eTactile.electrodeSize, eTactile.electrodeSize); 
        parent.fill(0,255,255);
        
        if (eTactile.display){
        PApplet.println("Electrode ", number ," position:- x: ", x, ", y: ",y);
        }
        
        parent.fill(255,255,255);
        parent.text(number, x-4, y+2);
        
        }
    }
    
    void visualizeArrayPattern3D() {
        parent.fill(0, 0, 255); // blue color for the electrodes
        parent.noStroke();
        
        // Loop through the electrode points and draw each as a circle
        for (int i = 0; i < electrodes.size(); i++) {
          JSONObject electrode = electrodes.getJSONObject(i);
          float x = electrode.getFloat("x");
          float y = electrode.getFloat("y");
          float z = electrode.getFloat("z");
          
          electrode_positions[i][0] = x; // Store x position
          electrode_positions[i][1] = y; // Store y position
          
          
            if (eTactile.isInsideShape3D(x,y,z)){
              eTactile.elecs_data[i] = 1;
              parent.fill(255,0,0);
            }
            
            else{
              eTactile.elecs_data[i] = 0;
              parent.fill(0,0,255);
            }
          
            parent.pushMatrix();
            parent.translate(x, y, z);
            parent.sphere(eTactile.electrodeRadius); // Draw small spheres for electrodes
            parent.popMatrix();
          
          if (eTactile.display){
            PApplet.println("Electrode ", i ," position:- x: ", x, ", y: ",y, "z: ",z);
          }
        }
      }
    
    void visualizeBoardShape() {
        // Set color for the shape outline
        parent.stroke(0);
        parent.strokeWeight(2);
        parent.fill(150, 150, 150); 
        
        // Initialize min and max values
        float x_min = Float.MAX_VALUE;
        float x_max = Float.MIN_VALUE;
        float y_min = Float.MAX_VALUE;
        float y_max = Float.MIN_VALUE;
        
        // First pass: Calculate min and max values of x and y
        for (int i = 0; i < eTactile.coordinates.size(); i++) {
            JSONObject point = eTactile.coordinates.getJSONObject(i);
            float x = (point.getFloat("x") * 10 + 500);
            float y = (900 - (point.getFloat("y") * 10 + 500));
            
            if (x < x_min) x_min = x;
            if (x > x_max) x_max = x;
            if (y < y_min) y_min = y;
            if (y > y_max) y_max = y;
        }
        
        // Determine if scaling is needed
        boolean scaleX = (x_min < 100 || x_max > 900);
        boolean scaleY = (y_min < 100 || y_max > 800);
        
        // Calculate scaling factors
        float scaleFactorX = 1.0f;
        float scaleFactorY = 1.0f;
        
        if (scaleX) {
            float desiredWidth = 900 - 100;
            float currentWidth = x_max - x_min;
            scaleFactorX = desiredWidth / currentWidth;
        }
        
        if (scaleY) {
            float desiredHeight = 800 - 100;
            float currentHeight = y_max - y_min;
            scaleFactorY = desiredHeight / currentHeight;
        }
        
        // Use the smaller scaling factor to maintain aspect ratio
        scaleFactor = PApplet.min(scaleFactorX, scaleFactorY);
        eTactile.scaleFactor = scaleFactor;
        
        // Start drawing the shape
        parent.beginShape();
        
        // Second pass: Add scaled vertices to the shape
        for (int i = 0; i < eTactile.coordinates.size(); i++) {
            JSONObject point = eTactile.coordinates.getJSONObject(i);
            
            if (scaleX || scaleY){
                needToScale = true;
                float x = ((point.getFloat("x") * scaleFactor) * 10 + 500);
                float y = (900 - ((point.getFloat("y") * scaleFactor) * 10 + 500));
                
                parent.vertex(x, y); // Add each vertex
            }
            
            else{
                float x = (point.getFloat("x") * 10 + 500);
                float y = (900 - (point.getFloat("y") * 10 + 500));
                
                parent.vertex(x, y); // Add each vertex
            }
            
            
            
        }
        
        // End and close the shape
        parent.endShape(PApplet.CLOSE);
        eTactile.needToScale = needToScale;
    }
    

    
    void visualize3DObject() {
        parent.shape(eTactile.obj_shape);
    }
    
    
    float[] getElectrodePosition(int index) {
        return electrode_positions[index];
    }
    
}
