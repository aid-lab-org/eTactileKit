package eTactile;

import peasy.*;
import processing.core.*;
import processing.data.*;

import java.util.Arrays;

public class ETactile {

    // Core dependencies
    LoadData dataLoader;
    SaveToJson saveJson;
    Visualizer visualizer;
    ShapeChecker3D shapeChecker;
    PeasyCam cam;

    // Electrode and pattern data
    int[] elecs_data;
    int[] prev_elecs_Data;
    int electrodes_number;
    float electrodeSize;
    float electrodeRadius;
    int[] mapping_func;

    float scaleFactor;
    boolean needToScale = false;

    PShape obj_shape; // 3D model

    JSONArray outer_array = new JSONArray();
    JSONArray coordinates, electrodes;
    int delay_time;
    int frequency = 75;
    int stimMode = 1; // 1-Anodic, 0-Cathodic

    int pattern_red, pattern_green, pattern_blue;
    int pattern_type = 0;
    boolean blink_state = true;
    int[] electrode_to_activate;

    boolean simulation = true;
    boolean execution = true;
    
    String output_name;

    int iteration = 0;
    boolean started_writing = false;

    boolean display;
    boolean saved = false;

    PApplet parent;

    public ETactile(PApplet parent) {
        this.parent = parent;
        parent.registerMethod("pre", this);
        parent.registerMethod("draw", this);

        shapeChecker = this::defaultIsInsideShape3D;
    }

    public void pre() {
        setBackground(0);
    }

    public void draw() {
        if (parent.g.is3D()) {
            create_pattern_3D();
        } else {
            create_pattern_2D();
        }
    }

    void create_pattern_2D() {

        visualizer.visualizeArrayPattern();
        iteration += 1;

        if (!Arrays.equals(elecs_data, prev_elecs_Data)) {
            if (!started_writing) {
                iteration = 0;
                started_writing = true;
                System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
            } else {
                int delay_time_n = iteration * delay_time;
                saveJson.saveDataToJson(outer_array, delay_time_n, prev_elecs_Data, frequency, stimMode);
                System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
                iteration = 0;
            }
        }

        parent.delay(delay_time);
    }

    void create_pattern_3D() {
        visualizer.visualize3DObject();
        visualizer.visualizeArrayPattern3D();
        iteration += 1;

        if (!Arrays.equals(elecs_data, prev_elecs_Data)) {
            if (!started_writing) {
                iteration = 0;
                started_writing = true;
                System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
            } else {
                int delay_time_n = iteration * delay_time;
                saveJson.saveDataToJson(outer_array, delay_time_n, prev_elecs_Data, frequency, stimMode);
                System.arraycopy(elecs_data, 0, prev_elecs_Data, 0, elecs_data.length);
                iteration = 0;
            }
        }

        parent.delay(delay_time);
    }

    public void eTframedelay(int delay) {
        this.delay_time = delay;
    }

    public void eTfreq(int freq) {
        this.frequency = freq;
    }

    public void eTmode(String mode) {
        if (mode.equalsIgnoreCase("Cathodic") || mode.equalsIgnoreCase("C")) {
            stimMode = 0;
        } else if (mode.equalsIgnoreCase("Anodic") || mode.equalsIgnoreCase("A")) {
            stimMode = 1;
        } else {
            PApplet.println("Invalid argument for stimulation mode -> Defaulting to Anodic.");
        }
    }

    public void eTstrokeColour(int r, int g, int b) {
        this.pattern_red = r;
        this.pattern_green = g;
        this.pattern_blue = b;
        parent.stroke(r, g, b);
    }

    public void setBackground(int color) {
        parent.background(color);
        if (parent.g.is3D()) {
            visualizer.visualize3DObject();
            parent.noStroke();
        } else {
            visualizer.visualizeBoardShape();
        }
    }

    public void setBlinkState(boolean state) {
        this.blink_state = state;
    }

    public void toggleBlinkState() {
        this.blink_state = !blink_state;
    }

    public void activateElectrodes(int[] electrodes) {
        this.electrode_to_activate = electrodes;
    }

    public boolean isInsideShape2D(float x, float y, int i) {
        if (pattern_type == 0) {
            for (float j = x - electrodeSize / 100; j <= x + electrodeSize / 100; j++) {
                for (float k = y - electrodeSize / 100; k <= y + electrodeSize / 100; k++) {
                    int px = (int) j;
                    int py = (int) k;
                    int c = parent.get(px, py);
                    if (parent.red(c) != 150 && parent.green(c) != 150 && parent.blue(c) != 150) {
                        return true;
                    }
                }
            }
            return false;
        } else if (pattern_type == 1) {
            return blink_state;
        } else if (pattern_type == 2) {
            for (int electrode : electrode_to_activate) {
                if (electrode == i && blink_state) return true;
            }
            return false;
        } else {
            return false;
        }
    }

    public void patternType(String type) {
        switch (type) {
            case "G": pattern_type = 0; break;
            case "B": pattern_type = 1; break;
            case "S": pattern_type = 2; break;
        }
    }

    public void terminate() {
        if (!saved){
            save_pattern();
            PApplet.println("Pattern created and saved to JSON file.");
            saved = true;
        }
    }

    public void save_pattern() {
        saveJson.saveJSONfile(outer_array);
    }

    public void setup2D(String arrayPatternFile, String outputFile) {
        dataLoader = new LoadData(parent);
        saveJson = new SaveToJson(parent, this);

        dataLoader.load2D(arrayPatternFile);

        electrodes_number = dataLoader.electrodes_number;
        elecs_data = new int[electrodes_number];

        setupEnv();

        display = true;
        visualizer.visualizeBoardShape();
        visualizer.visualizeArrayPattern();
        display = false;

        output_name = outputFile;
    }

    public void setup3D(String electrodesLocFile, String object3D, String outputFile) {
        dataLoader = new LoadData(parent);
        saveJson = new SaveToJson(parent, this);

        cam = new PeasyCam(parent, 500);
        cam.setMinimumDistance(100);
        cam.setMaximumDistance(2000);

        dataLoader.load3D(electrodesLocFile,object3D);
        electrodes_number = dataLoader.electrodes_number;
        elecs_data = new int[electrodes_number];

        setupEnv();

        obj_shape = dataLoader.obj_shape;

        display = true;
        visualizer.visualize3DObject();
        visualizer.visualizeArrayPattern3D();
        display = false;

        
        parent.lights();

        output_name = outputFile;
    }

    private void setupEnv() {
        electrodes_number = dataLoader.electrodes_number;
        coordinates = dataLoader.coordinates;
        electrodes = dataLoader.electrodes;
        electrodeRadius = dataLoader.electrodeRadius;
        mapping_func = dataLoader.mapping_func;

        prev_elecs_Data = new int[electrodes_number];

        visualizer = new Visualizer(parent, this);
        saveJson.json = new JSONObject();
        outer_array = new JSONArray();

        parent.background(0);
        parent.noStroke();
    }

    public void setIsInsideShape3D(ShapeChecker3D checker){
        shapeChecker = checker != null ? checker : this::defaultIsInsideShape3D;
      }

    boolean defaultIsInsideShape3D(float x, float y, float z){
        return false;
        }

    boolean isInsideShape3D(float x, float y, float z){
        return shapeChecker.isInsideShape3D(x, y, z);
      }
}
