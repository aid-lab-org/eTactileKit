#include "communication.h"

bool deviceConnected = false;

#if defined(SERIAL_COMMUNICATION)

void initCommunication() {
  // Default RX buffer is 256 B; the parser waits for a full payload before
  // reading, and the largest payload (stim pattern at MAX_ELECTRODE_NUM) is
  // 512 B. Must be set before Serial.begin().
  Serial.setRxBufferSize(1024);
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

void writeBytes(const byte* data, size_t len) {
  if (!deviceConnected) return;
  Serial.write(data, len);
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
bool wifiSTAMode = false;
AsyncUDP discoveryUdp;
char deviceId[7] = {0};

// Register the mDNS host + service under a per-board unique name so multiple kits
// coexist. Kept as a helper because both STA and AP paths advertise identically.
static void startMdns(const String& hostname) {
  if (MDNS.begin(hostname.c_str())) {
    MDNS.setInstanceName(String("eTactileKit ") + deviceId);
    MDNS.addService("etactilekit", "tcp", SERVER_PORT);
    MDNS.addServiceTxt("etactilekit", "tcp", "id", (const char*)deviceId); // browsable by unique ID
  }
}

// Listen for UDP discovery probes and reply (unicast) with this board's identity + IP.
// The onPacket callback runs on the async network task (Core 0), so it adds no work to
// runEtactileKit() and cannot delay the stimulation ISR. It only fires when a probe arrives.
static void startDiscoveryResponder() {
  if (discoveryUdp.listen(DISCOVERY_PORT)) {
    discoveryUdp.onPacket([](AsyncUDPPacket &packet) {
      // Only answer genuine probes; ignore anything else that lands on this port.
      if (packet.length() >= 4 && memcmp(packet.data(), DISCOVERY_PROBE, 4) == 0) {
        IPAddress ip = wifiSTAMode ? WiFi.localIP() : WiFi.softAPIP();
        // ;-separated key=value line, parsed identically by the Python and Unity clients.
        packet.printf("%s;id=%s;name=%s-%s;ip=%s;port=%d;mode=%s;fw=1.0",
                      DISCOVERY_REPLY_PREFIX, deviceId,
                      MDNS_HOSTNAME, deviceId,
                      ip.toString().c_str(), SERVER_PORT,
                      wifiSTAMode ? "STA" : "AP");
      }
    });
  }
}

void initCommunication() {
  // Derive a stable, unique ID from the LAST three octets of the factory MAC. getEfuseMac()
  // packs the MAC least-significant-octet first, so its low 24 bits are the OUI (vendor prefix)
  // that is SHARED across boards — using them made every kit report the same ID. The upper three
  // octets (mac[3..5], the NIC-specific part) are unique per chip and match the tail of the MAC
  // shown in the router's client list. Constant across reboots and STA/AP mode.
  uint64_t mac = ESP.getEfuseMac();
  snprintf(deviceId, sizeof(deviceId), "%02X%02X%02X",
           (uint8_t)(mac >> 24), (uint8_t)(mac >> 32), (uint8_t)(mac >> 40));
  String hostname = String(MDNS_HOSTNAME) + "-" + deviceId; // etactilekit-A1B2C3

  // --- Attempt Station mode first (DHCP, no static IP) ---
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(hostname.c_str());
  WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASS);

  wl_status_t result = (wl_status_t)WiFi.waitForConnectResult(WIFI_STA_TIMEOUT_MS);

  if (result == WL_CONNECTED) {
    wifiSTAMode = true;
    startMdns(hostname); // reachable as etactilekit-<ID>.local
  } else {
    // --- Fallback to Access Point mode with a unique per-board SSID ---
    WiFi.disconnect(true);
    WiFi.mode(WIFI_AP);
    String apSsid = String(WIFI_AP_SSID_PREFIX) + deviceId; // eTactileKit_A1B2C3
    WiFi.softAP(apSsid.c_str(), WIFI_AP_PASS);
    wifiSTAMode = false;
    startMdns(hostname);
  }

  // UDP discovery responder (event-driven; no main-loop or ISR cost)
  startDiscoveryResponder();

  // TCP server starts regardless of mode
  server.begin();
  server.setNoDelay(true);
}

// Helper: Maintains the client object
void checkClientConnection() {
  if (!client || !client.connected()) {
    deviceConnected = false;
    // Try to accept a new client
    WiFiClient newClient = server.available();
    if (newClient) {
      client = newClient;
      client.setNoDelay(true); // Disable for lower latency
      deviceConnected = true;
    }
  }
}

void writeInt_8(byte val) {
  checkClientConnection();
  if (!deviceConnected) return;
  client.write(val);
}

void writeInt_16(uint16_t val) {
  checkClientConnection();
  if (!deviceConnected) return;
  // Send Little Endian (Low byte first)
  byte arr[2] = { (byte)(val & 0xFF), (byte)((val >> 8) & 0xFF) };
  client.write(arr, 2);
}

byte readInt_8() {
  if (!deviceConnected) return 0;
  return client.read();
}

uint16_t readInt_16() {
  if (!deviceConnected) return 0;
  // We need at least 2 bytes. This should be called after confirming data is available.
  byte low = client.read();
  byte high = client.read();
  return (uint16_t)(low | (high << 8));
}

void writeBytes(const byte* data, size_t len) {
  checkClientConnection();
  if (!deviceConnected) return;
  client.write(data, len);
}

int isDataAvailable() {
  checkClientConnection();
  if (client && client.connected()) {
    return client.available(); // Return number of bytes available to read
  }
  return 0;
}

#endif

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

void writeBytes(const byte* data, size_t len) {
  if (!deviceConnected) return;
  pTxCharacteristic->setValue((uint8_t*)data, len);
  pTxCharacteristic->notify();
}

int isDataAvailable() {
  return bleRxBuffer.available();
}
#endif