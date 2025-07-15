/*ETactileKit - Visualization and Execution programme

TimerHandler :- used to keep the timing in track

Functions:  handleTimer()
            getExecutingTime()
            getLocalTimer()
            getDeactivateFlag()
*/

class TimerHandler {
  public int      executing_time;
  //public int      local_timer;
  public boolean  deactivate_flag;
  

  TimerHandler(int executing_time, boolean deactivate_flag) {
    this.executing_time    = executing_time;
    //this.local_timer       = local_timer;
    this.deactivate_flag   = deactivate_flag;
  }

  public void handleTimer(int delay_time, int delayOff) {
    /*Function for count the time and update localTimer
    Inputs:    delay_time    - ON time or OFF time that given by ElectrodeSwitch
               delayOff      - OFF time for check wether if it is invalid input if deactivate_flag is false (i.e. negative)
    */  
    
    int elapsed_time = millis() - executing_time;  // Calculate the executed time of the current pattern
    
    if (elapsed_time > delay_time) {
      if (!deactivate_flag && delayOff > 0) {
        deactivate_flag = true;
      } 
      else {
        local_timer       = (local_timer + 1) % dataLoader.patterns.size();
        deactivate_flag   = false;
      }
      executing_time = millis();
    }
  }


  public int getExecutingTime() {
    return executing_time;
  }


  public int getLocalTimer() {
    return local_timer;
  }


  public boolean getDeactivateFlag() {
    return deactivate_flag;
  }
}
