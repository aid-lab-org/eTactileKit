/*ETactileKit - Visualization and Execution programme

SerialComm :- used to communicate with hardware

Functions:  setupPort()
            sendByte()
            sendByteArray()
            readByte()
            
 NOTE: Change the portName according to yours.
            
*/

import processing.serial.*;

class SerialComm {
  
  final int baud_rate = 921600;
  String    port_name;
  
  Serial port;
  
  SerialComm(PApplet parent, String port_name) {
    this.port_name = port_name;
    SetupPort(parent);
  }
  
  //Initialize Serial Port
  private void SetupPort(PApplet parent) {
    try {
      port = new Serial(parent, port_name, baud_rate);
      port.clear();
      println("Serial port initialized succesfully.");
      
    } catch (Exception e) {
      System.err.println("Error initializing serial port: " + e.getMessage());
    }
  }
  
  // Close the serial port
  public void closePort() {
    if (port != null) {
      port.stop();
      println("Serial port closed.");
    } else {
      System.err.println("Serial port not initialized.");
    }
  }
  
  //send a single byte 
  public void sendByte(byte command)
  {
    if (port != null) {
      // println("byte sent");
      port.write(command);
    } else {
      System.err.println("Serial port not initialized.");
    }
  }
  
  //send a byte array
  public void sendByteArray(byte[] pattern) {
    if (port != null) {
      port.write(pattern);
    } else {
      System.err.println("Serial port not initialized.");
    }
  }
  
  //read a single byte
  int readByte() {
    if (port == null){
      return 0;
    }
    int received_data = 0;
    if (port.available() > 0){
      received_data = port.read();
    }
    return received_data;
  }
  
  //read a single byte with timeout
  int readByteWithTimeout(float time_out){
    if (port == null){
      return 0;
    }
    int received_data = 0;
    long start_time = millis();
    while (millis() - start_time < time_out * 1000){
      if (port.available() > 0){
        received_data = port.read();
        break;
      }
      delay(1);
    }
    return received_data;
  }
}
