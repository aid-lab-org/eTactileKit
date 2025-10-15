/*ETactileKit - Visualization and Execution programme

KeyPressHandler :- used to handle the keyboard inputs

Functions:  handleKeyPress()
            getVolume()
            getWidth()
*/


class KeyPressHandler {
  
  private int volume;
  private int width_;
  private int polarity;

  // Constructor
  KeyPressHandler() {
    volume = 100;
    width_ = 100;
    polarity = 1;
  }

  // Method to handle key presses and update Volume and Width
  void handleKeyPress(char key) {
    if (key == CODED) {
      if (keyCode == UP) {
        
        if (proceed_et && volume >= upper_thresh_hight && !allowed){
          uiManager.showExceedWarningDialog(volume, width_, upper_thresh_hight, upper_thresh_width);
          return;
        }
        
        else{
        volume = volume + 1;
        if(volume > 350)   volume = 350;
        eTactile.send_stimulation_pulse_height(volume);
        }
      } 
      
      
      else if (keyCode == DOWN) {
        volume = volume - 1;
        if(volume < 0)     volume = 0;
        eTactile.send_stimulation_pulse_height(volume);
      } 
      else if (keyCode == RIGHT) {
        
        if (proceed_et && width_ >= upper_thresh_width && !allowed){
          uiManager.showExceedWarningDialog(volume, width_, upper_thresh_hight, upper_thresh_width);
          return;
        }
        
        else{
          width_ = width_ + 1;
          if(width_ > 350)   width_ = 350;
          eTactile.send_stimulation_pulse_width(width_);
          } 
      }
      
      else if (keyCode == LEFT) {
        width_ = width_ -1;
        if(width_ < 0)     width_ = 0;
        eTactile.send_stimulation_pulse_width(width_);
      } 
        
      print("Volume: ",volume);
      println(", Width: ",width_);
    } 
    
    else if (key == ' '){
      volume    = 100;
      width_    = 100;
      polarity  = 1;
      eTactile.send_stimulation_pulse_height(volume);
      eTactile.send_stimulation_pulse_width(width_);
      eTactile.send_stimulation_polarity(1);
    } 
    
    //else if (key == 'l') {
    //  volume = volume + 5;
    //  if(volume > 250) volume = 250;
    //  print("Volume: ",volume);
    //}
    
    //else if (key == 'k') {
    //  volume = volume + 1;
    //  if(volume > 250) volume = 250;
    //  print("Volume: ",volume);
    //}
    
    //else if (key == 'j') {
    //  volume = volume - 1;
    //  if(volume <0) volume = 0;
    //  print("Volume: ",volume);
    //}
    
    //else if (key == 'h') {
    //  volume = volume - 5;
    //  if(volume <0) volume = 0;
    //  print("Volume: ",volume);
    //}
    
    //else if (key == 'a') {
    //  polarity = 1;
    //}
    
    //else if (key == 'c') {
    //  polarity = 0;
    //}
    
    else{
      return;
    }
  }

  // Getter method for Volume
  int getVolume() {
    return volume;
  }

  // Getter method for Width
  int getWidth() {
    return width_;
  }

  int getPolarity() {
    return polarity;
  }
}
