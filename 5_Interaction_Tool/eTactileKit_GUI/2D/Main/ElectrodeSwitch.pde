/*ETactileKit - Visualization and Execution programme

ElectrodeSwitch :- used to switch electrode states

Functions:  updateSwitchState()
            getDelayTime()
            resetElectrodes()
*/


class ElectrodeSwitch {  
  private int delay_time;
  
  void updateSwitchState(byte[] switchState, JSONArray patternData, int delayOn, int delayOff, boolean deactivate_flag) {
    /*Function for update the state of each electrodes
    Inputs: SwitchState      - the byte array REFERENCE for store electrode state (1:ON or 0:OFF)
            patternData      - JSON array that have the electrode activation details
            delayOn          - ON time
            delayOff         - All electrodes OFF time
            deactivate flag  - flag for identify all off time (if true: all electrode OFF, false: pattern in patternData)
            
    This function sets the electrodes states based on patternData and the deactivatr_flag
    */
    
    if (deactivate_flag) {
      for (int ch = 0; ch < patternData.size(); ch++) {
        switchState[ch]  = 0;
        delay_time       = delayOff;
      }
    } else {
      for (int ch = 0; ch < patternData.size(); ch++) {
        switchState[ch]  = (byte) patternData.getInt(ch);
        delay_time       = delayOn;
      }
    }
  }
  
  
  int getDelayTime() {
    return delay_time;
  }
  
  void resetElectrodes(byte[] switchState){
    for (int i = 0; i < eTactile.number_of_electrodes; i++) {
    switchState[i] = 0;
    }
  }
}
