/*ETactileKit - Visualization and Execution programme

SerialComm :- used to communicate with hardware

Functions:  setupPort()
            sendByte()
            sendByteArray()
            readByte()
            
 NOTE: Change the portName according to yours.
            
*/

import processing.serial.*;
import java.nio.ByteBuffer;

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

  public void flushPort() {
    if (port != null) {
      port.clear();
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
  
  // Send a 16-bit integer as 2 bytes in little-endian format
  public void sendInt16(int value) {
      if (port != null) {
          // Little-endian: send low byte first, then high byte
          port.write((byte)(value & 0xFF));        // Low byte
          port.write((byte)((value >> 8) & 0xFF)); // High byte
      } else {
          System.err.println("Serial port not initialized.");
      }
  }
  
      // Read 16-bit integer in little-endian format (2 bytes)
    public int readInt16LittleEndian() {
        if (port != null && port.available() >= 2) {
            int lowByte = port.read() & 0xFF;   // Read low byte first
            int highByte = port.read() & 0xFF;  // Read high byte second
            return (highByte << 8) | lowByte;   // Combine bytes
        }
        return -1; // Return -1 if not enough data available
    }
  
  //public void sendBytes(int val, int numBytes) {
  //  if (port != null) {
  //    byte[] data = new byte[numBytes];
  
  //    // Always little endian: least significant byte first
  //    for (int i = 0; i < numBytes; i++) {
  //      data[i] = (byte)(val >> (8 * i));
  //    }
  
  //    port.write(data); // send the byte array
  //  } else {
  //    System.err.println("Serial port not initialized.");
  //  }
  //}
  
  
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
      delay(1); //for stability
    }
    return received_data;
  }
}
