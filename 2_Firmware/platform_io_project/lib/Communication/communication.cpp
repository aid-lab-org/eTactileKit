#include "communication.h"

bool deviceConnected = false;

#if defined(BLE_COMMUNICATION)
BLEServer* pServer = NULL;
BLECharacteristic* pTxCharacteristic = NULL;
BLECharacteristic* pRxCharacteristic = NULL;
RxBuffer bleRxBuffer;

// Callback for connection status
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
    };
    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      // Restart advertising so Python can reconnect
      pServer->getAdvertising()->start(); 
    }
};

// Callback for receiving data from Python
class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      std::string rxValue = pCharacteristic->getValue();
      if (rxValue.length() > 0) {
        for (int i = 0; i < rxValue.length(); i++) {
          bleRxBuffer.write(rxValue[i]); // Push to Ring Buffer
        }
      }
    }
};

void initCommunication() { 
  BLEDevice::init(DEVICE_NAME); // Name of your device
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create TX Characteristic (Sending to Client)
  pTxCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID_TX,
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pTxCharacteristic->addDescriptor(new BLE2902());

  // Create RX Characteristic (Receiving from Client)
  pRxCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID_RX,
                      BLECharacteristic::PROPERTY_WRITE
                    );
  pRxCharacteristic->setCallbacks(new MyCallbacks());

  pService->start();
  
  // Start Advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  // pAdvertising->setMinPreferred(0x00);  
  // pAdvertising->setMinPreferred(0x1F);
  BLEDevice::startAdvertising();
}

void writeInt_8(byte val) {
  if (deviceConnected) {
    // BLE notifications usually expect an array. 
    // Sending byte by byte is overhead-heavy but fits your request structure.
    pTxCharacteristic->setValue(&val, 1);
    pTxCharacteristic->notify();
  }
}

void writeInt_16(uint16_t val) {
  if (deviceConnected) {
    byte arr[2] = { (byte)(val & 0xFF), (byte)((val >> 8) & 0xFF) };
    pTxCharacteristic->setValue(arr, 2);
    pTxCharacteristic->notify();
  }
}

byte readInt_8() {
  int v = bleRxBuffer.read();
  if (v == -1) return 0;
  return (byte)v;
}

uint16_t readInt_16() {
  byte low = readInt_8();
  byte high = readInt_8();
  return (uint16_t)(low | (high << 8));
}

int isDataAvailable() {
  return bleRxBuffer.available();
}
#endif

#if defined(SERIAL_COMMUNICATION)

void initCommunication() {
  Serial.begin(BAUD_RATE);
  deviceConnected = true;
}

void writeInt_8(byte val) {
  if (!deviceConnected) return;
  Serial.write(val);
}

void writeInt_16(uint16_t val) {
  if (!deviceConnected) return;
  byte arr[2] = { (byte)(val & 0xFF), (byte)((val >> 8) & 0xFF) };
  Serial.write(arr, 2);   // Send the array of bytes in the little-endian order
}

byte readInt_8() {
  return Serial.read();
}

uint16_t readInt_16() {
  byte arr[2];
  Serial.read(arr, 2); // Read two bytes into the array
  return (uint16_t)(arr[0] | (arr[1] << 8)); // Combine the two bytes into a single uint16_t
}

int isDataAvailable() {
  return Serial.available();
}
#endif

#if defined(WIFI_COMMUNICATION)
WiFiServer server(SERVER_PORT);
WiFiClient client;

void initCommunication() {
  // 1. Set up the ESP32 as an Access Point
  WiFi.softAP(WIFI_SSID, WIFI_PASS);

  // 2. Start the TCP Server
  server.begin();

}

// Helper: Maintains the client object
void checkClientConnection() {
  if (!client || !client.connected()) {
    deviceConnected = false;
    // Try to accept a new client
    WiFiClient newClient = server.available();
    if (newClient) {
      client = newClient;
      deviceConnected = true;
    }
  }
}

void writeInt_8(byte val) {
  checkClientConnection();
  if (client && client.connected()) {
    client.write(val);
  }
}

void writeInt_16(uint16_t val) {
  checkClientConnection();
  if (client && client.connected()) {
    // Send Little Endian (Low byte first)
    byte arr[2] = { (byte)(val & 0xFF), (byte)((val >> 8) & 0xFF) };
    client.write(arr, 2);
  }
}

byte readInt_8() {
  checkClientConnection();
  if (client && client.available() > 0) {
    return client.read();
  }
  return 0;
}

uint16_t readInt_16() {
  checkClientConnection();
  // We need at least 2 bytes. 
  // In a blocking scenario, we might wait, but here we check availability.
  if (client && client.available() >= 2) {
    byte low = client.read();
    byte high = client.read();
    return (uint16_t)(low | (high << 8));
  }
  return 0; 
}

int isDataAvailable() {
  checkClientConnection();
  if (client && client.connected()) {
    return client.available();
  }
  return 0;
}

#endif