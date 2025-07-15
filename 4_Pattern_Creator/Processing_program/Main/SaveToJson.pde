class SaveToJson {
    JSONObject json;
    JSONArray outer_array;
    JSONArray outer_inner_array;
    JSONObject inner_object;
    JSONObject param_object;
    JSONObject delay_object;
    JSONArray data_array;

    SaveToJson() {
        outer_array = new JSONArray();
    }

    void saveDataToJson(JSONArray outer_array, int time_difference, int[] elecs_data, int frequency, int stim_mode) {
        outer_inner_array = new JSONArray();
        inner_object = new JSONObject();
        data_array = new JSONArray();
        param_object = new JSONObject();
        delay_object = new JSONObject();

        for (int i = 0; i < elecs_data.length; i++) {
            data_array.setInt(i, elecs_data[i]);
        }

        inner_object.setJSONArray("pattern", data_array);
        delay_object.setInt("ON", time_difference);
        delay_object.setInt("OFF", 0);
        param_object.setInt("frequency", frequency);
        param_object.setInt("stim_mode", stim_mode);
        inner_object.setJSONObject("params", param_object);
        inner_object.setJSONObject("delay", delay_object);
        outer_inner_array.append(inner_object);
        outer_array.append(outer_inner_array);
    }

    void saveJSONfile(JSONArray outer_array) {
        json.setBoolean("Simulation", eTactile.simulation);
        json.setBoolean("Execution", eTactile.execution);
        println("outer array size: ", outer_array.size());
        json.setJSONArray("Pattern_Data", outer_array);
        saveJSONObject(json, eTactile.output_name+".json");
    }
}
