#include "communication.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <AsyncUDP.h>
#include "esp_intr_alloc.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "soc/periph_defs.h"
#include "lwip/sockets.h"
#include "hal/usb_serial_jtag_ll.h"

#if !ARDUINO_USB_MODE
#error "Select USB Mode 'Hardware CDC and JTAG': the firmware drives the USB-Serial-JTAG port directly"
#endif

#define WIFI_POLL_MS 10  // How often the command task checks for a new TCP client or a dropped one

extern "C" bool g_usb_print;  // ESP32-S3 ROM: ROM printf also writes to the USB-Serial-JTAG endpoint

volatile Link activeLink = LINK_NONE;
uint32_t linkGeneration = 0;

/************************************************************************* */
/*USB serial link                                                          */
/*The USB-Serial-JTAG endpoint is driven directly: replies are written     */
/*straight into its 64-byte packet FIFO and received bytes are read out of */
/*it by the command task. The only USB interrupt is a wake-up for that     */
/*task, allocated on core 0.                                               */
/************************************************************************* */
#define SERIAL_PACKET        USB_SERIAL_JTAG_PACKET_SZ_BYTES  // Endpoint FIFO size, one USB packet
#define SERIAL_RX_SIZE       1024   // Receive ring (power of two); holds the largest frame, 513 B
#define SERIAL_TX_TIMEOUT_US 50000  // Replies are dropped once the host has not collected a packet for this long

static uint8_t serialRx[SERIAL_RX_SIZE];
static uint32_t serialRxHead = 0;      // Free-running write index into serialRx
static uint32_t serialRxTail = 0;      // Free-running read index into serialRx
static int64_t serialTxOkUs = 0;       // Last time the endpoint FIFO had room for a packet
static bool serialOpen = false;        // A host has the serial port open
static bool serialRefused = false;     // The open port was refused because WiFi owned the board
static TickType_t serialSeenTick = 0;  // Last time the host polled the port or sent data
static TaskHandle_t serialWaiter = NULL;  // Task woken by serialRxIsr (the task that ran initCommunication)

// Wakes the waiting task when the host sends a packet. The data stays in the endpoint FIFO for
// serialPoll(); the interrupt disables itself until waitForHostData() enables it again.
static void IRAM_ATTR serialRxIsr(void *) {
  usb_serial_jtag_ll_disable_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
  BaseType_t woken = pdFALSE;
  vTaskNotifyGiveFromISR(serialWaiter, &woken);
  if (woken) portYIELD_FROM_ISR();
}

// Forces the host to enumerate the port again, so a host that was mid-command when the board
// restarted has to reopen it and the parser starts on a command boundary.
static void initSerial() {
  usb_serial_jtag_ll_disable_intr_mask(USB_SERIAL_JTAG_LL_INTR_MASK);
  pinMode(USB_DM_GPIO_NUM, OUTPUT_OPEN_DRAIN);
  pinMode(USB_DP_GPIO_NUM, OUTPUT_OPEN_DRAIN);
  digitalWrite(USB_DM_GPIO_NUM, LOW);
  digitalWrite(USB_DP_GPIO_NUM, LOW);
  delay(10);                                    // Long enough for the host to see a disconnect
  USB_SERIAL_JTAG.conf0.phy_sel = 0;            // Internal PHY
  USB_SERIAL_JTAG.conf0.pad_pull_override = 0;  // Hardware controls the D+/D- pull resistors
  USB_SERIAL_JTAG.conf0.dp_pullup = 1;          // Full-speed device
  USB_SERIAL_JTAG.conf0.usb_pad_enable = 1;     // Hand the pins back to the USB PHY
  while (usb_serial_jtag_ll_rxfifo_data_available()) {
    (void)USB_SERIAL_JTAG.ep1.rdwr_byte;
  }
  usb_serial_jtag_ll_clr_intsts_mask(USB_SERIAL_JTAG_LL_INTR_MASK);
}

// Moves received packets from the endpoint FIFO into serialRx while a whole packet fits. Bytes left
// in the FIFO make the endpoint refuse (NAK) the host's next packet until they are read, so the
// host is held off instead of anything being dropped. Returns true if any bytes were moved.
static bool serialPoll() {
  const uint32_t start = serialRxHead;
  while (SERIAL_RX_SIZE - (serialRxHead - serialRxTail) >= SERIAL_PACKET &&
         usb_serial_jtag_ll_rxfifo_data_available()) {
    for (int i = 0; i < SERIAL_PACKET && usb_serial_jtag_ll_rxfifo_data_available(); i++) {
      serialRx[serialRxHead++ & (SERIAL_RX_SIZE - 1)] = USB_SERIAL_JTAG.ep1.rdwr_byte;
    }
  }
  return serialRxHead != start;
}

static byte serialRead() {
  if (serialRxHead == serialRxTail) return 0;
  return serialRx[serialRxTail++ & (SERIAL_RX_SIZE - 1)];
}

static void drainSerial() {
  serialRxTail = serialRxHead;
  while (usb_serial_jtag_ll_rxfifo_data_available()) {
    (void)USB_SERIAL_JTAG.ep1.rdwr_byte;
  }
}

// True once the host has collected the previous packet. A host that stops collecting (port closed
// mid-reply, PC asleep) is waited for up to SERIAL_TX_TIMEOUT_US; after that, packets are dropped
// without waiting until it collects one again.
static bool serialTxReady() {
  while (!usb_serial_jtag_ll_txfifo_writable()) {
    sampleHostPresence();
    if (esp_timer_get_time() - serialTxOkUs > SERIAL_TX_TIMEOUT_US) return false;
  }
  serialTxOkUs = esp_timer_get_time();
  return true;
}

// Sends full packets, then the shorter remainder. The host holds a transfer that ends on a full
// packet until a shorter one follows, so a reply never ends on one: when its length is a multiple
// of 64, its last 64 bytes go out as packets of 63 and 1 bytes.
static void serialWrite(const byte* data, size_t len) {
  while (len > 0) {
    size_t n = len < SERIAL_PACKET ? len : SERIAL_PACKET;
    if (len == SERIAL_PACKET) n--;
    if (!serialTxReady()) return;  // The host stopped reading; drop the rest of the reply
    n = usb_serial_jtag_ll_write_txfifo(data, n);
    usb_serial_jtag_ll_txfifo_flush();
    data += n;
    len -= n;
  }
}

// While a host has the port open, its CDC driver keeps polling the IN endpoint, which latches
// IN_TOKEN_REC_IN_EP1 in the raw interrupt status (the interrupt itself stays disabled), and every
// packet it sends latches SERIAL_OUT_RECV_PKT.
static bool serialHostActive() {
  const uint32_t seen = USB_SERIAL_JTAG.int_raw.val &
                        (USB_SERIAL_JTAG_INTR_TOKEN_REC_IN_EP1 | USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
  if (seen) usb_serial_jtag_ll_clr_intsts_mask(seen);
  return seen != 0;
}

void sampleHostPresence() {
  if (serialHostActive()) {
    serialSeenTick = xTaskGetTickCount();
    serialOpen = true;
  }
}

/************************************************************************* */
/*WiFi link                                                                */
/************************************************************************* */
static WiFiServer server(SERVER_PORT);
static WiFiClient client;
static AsyncUDP discoveryUdp;
static char deviceId[7] = {0};             // 6 hex chars (from MAC) + NUL, e.g. "A1B2C3"
static String hostname;                    // etactilekit-A1B2C3
static TaskHandle_t wifiTask = NULL;
static volatile bool wifiWanted = false;   // Command task -> radio task: the radio should be on
static volatile bool wifiReady = false;    // Radio task -> command task: the network is up
static volatile bool wifiSTAMode = false;  // true = STA mode, false = AP fallback
static TickType_t wifiPollTick = 0;
static volatile uint32_t staFailures = 0;     // Station disconnects: failed attempts, lost links, requested
static volatile uint32_t staMissedScans = 0;  // ... of which the router was not found

// Register the mDNS host + service under a per-board unique name so multiple kits coexist.
static void startMdns() {
  if (MDNS.begin(hostname.c_str())) {
    MDNS.setInstanceName(String("eTactileKit ") + deviceId);
    MDNS.addService("etactilekit", "tcp", SERVER_PORT);
    MDNS.addServiceTxt("etactilekit", "tcp", "id", (const char*)deviceId); // browsable by unique ID
  }
}

// Listen for UDP discovery probes and reply (unicast) with this board's identity + IP.
// The onPacket callback runs on the async UDP task, so it adds no work to the command task and
// cannot delay the stimulation interrupt. It only fires when a probe arrives.
static void startDiscoveryResponder() {
  if (discoveryUdp.listen(DISCOVERY_PORT)) {
    discoveryUdp.onPacket([](AsyncUDPPacket &packet) {
      // Only answer genuine probes; ignore anything else that lands on this port.
      if (packet.length() >= 4 && memcmp(packet.data(), DISCOVERY_PROBE, 4) == 0) {
        IPAddress ip = wifiSTAMode ? WiFi.localIP() : WiFi.softAPIP();
        // ;-separated key=value line, parsed identically by the Python and Unity clients.
        // busy=1 means another WiFi client currently owns the board.
        packet.printf("%s;id=%s;name=%s-%s;ip=%s;port=%d;mode=%s;busy=%d;fw=1.0",
                      DISCOVERY_REPLY_PREFIX, deviceId,
                      MDNS_HOSTNAME, deviceId,
                      ip.toString().c_str(), SERVER_PORT,
                      wifiSTAMode ? "STA" : "AP",
                      activeLink != LINK_NONE);
      }
    });
  }
}

// Counts Station disconnects and those that did not find the router. Runs in the Arduino WiFi
// event task.
static void onStaDisconnected(arduino_event_id_t, arduino_event_info_t info) {
  staFailures = staFailures + 1;
  if (info.wifi_sta_disconnected.reason == WIFI_REASON_NO_AP_FOUND) staMissedScans = staMissedScans + 1;
}

// Keeps the radio on (Station mode first, Access Point fallback) while wifiWanted is set and off
// otherwise. A kit that loses the router it had joined keeps rejoining it rather than falling back.
// Runs in its own task on core 0 beside the WiFi stack, so mode changes and the Station join never
// block command parsing or the stimulation interrupt on core 1. The actual WiFi mode is checked on
// every pass, because the library's own one-shot reconnect (first disconnect after boot) can change it.
static void wifiRadioTask(void *) {
  enum { RADIO_OFF, RADIO_JOINING, RADIO_STA, RADIO_AP_START, RADIO_AP } radio = RADIO_OFF;
  TickType_t joinTick = 0;
  TickType_t attemptTick = 0;
  uint32_t failuresSeen = 0;
  uint32_t missedAtJoin = 0;
  bool rejoining = false;   // The join follows a lost Station link: no Access Point fallback
  bool servicesStarted = false;

  for (;;) {
    bool up = false;
    if (!wifiWanted) {
      if (radio != RADIO_OFF || WiFi.getMode() != WIFI_MODE_NULL) {
        wifiReady = false;
        WiFi.mode(WIFI_OFF);
        radio = RADIO_OFF;
      }
    } else if (radio == RADIO_OFF || (radio == RADIO_STA && WiFi.status() != WL_CONNECTED)) {
      // --- Join the router in Station mode (DHCP, no static IP), at start and after losing it ---
      rejoining = radio == RADIO_STA;
      wifiReady = false;
      WiFi.mode(WIFI_STA);
      WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASS);
      joinTick = attemptTick = xTaskGetTickCount();
      failuresSeen = staFailures;
      missedAtJoin = staMissedScans;
      radio = RADIO_JOINING;
    } else if (radio == RADIO_JOINING) {
      const TickType_t now = xTaskGetTickCount();
      if (WiFi.status() == WL_CONNECTED) {
        wifiSTAMode = true;
        radio = RADIO_STA;
        up = true;
      } else if (!rejoining && (staMissedScans - missedAtJoin >= 2 ||
                                now - joinTick >= pdMS_TO_TICKS(WIFI_STA_TIMEOUT_MS))) {
        // The router was missing from two scans in this join window, or the window ran out
        WiFi.disconnect(true);
        WiFi.mode(WIFI_AP);
        radio = RADIO_AP_START;
      } else if (staFailures != failuresSeen || now - attemptTick >= pdMS_TO_TICKS(WIFI_STA_TIMEOUT_MS)) {
        // An attempt failed (a scan can miss a present router) or has not finished: try again
        failuresSeen = staFailures;
        attemptTick = now;
        WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASS);
      }
    } else if (radio == RADIO_AP_START) {
      // --- Fallback to Access Point mode with a unique per-board SSID ---
      String apSsid = String(WIFI_AP_SSID_PREFIX) + deviceId; // eTactileKit_A1B2C3
      if (WiFi.softAP(apSsid.c_str(), WIFI_AP_PASS)) {        // Retried on the next pass if it fails
        wifiSTAMode = false;
        radio = RADIO_AP;
        up = true;
      }
    } else if (radio == RADIO_AP && WiFi.getMode() != WIFI_MODE_AP) {
      // Access point only: a station side would scan for the router under it
      WiFi.mode(WIFI_AP);
      radio = RADIO_AP_START;
    }

    if (up) {
      if (!servicesStarted) {
        // Started once; both follow the network interface across later radio restarts.
        startMdns();                // reachable as etactilekit-<ID>.local
        startDiscoveryResponder();  // event-driven; no command-task or interrupt cost
        servicesStarted = true;
      }
      wifiReady = true;
    }
    ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(50));  // Woken early when the command task changes wifiWanted
  }
}

static void requestRadio(bool on) {
  wifiWanted = on;
  xTaskNotifyGive(wifiTask);
}

/************************************************************************* */
/*Link ownership                                                           */
/************************************************************************* */
static void openLink(Link link) {
  activeLink = link;
  linkGeneration++;
}

static void closeLink() {
  if (activeLink == LINK_WIFI) {
    client.stop();
  } else if (activeLink == LINK_SERIAL) {
    drainSerial();
    requestRadio(true);  // Listen on WiFi again
  }
  activeLink = LINK_NONE;
  linkGeneration++;
}

static void acceptWifiClient() {
  client = server.available();
  if (!client) return;
  server.end();  // Refuse further TCP clients while this one owns the board
  client.setNoDelay(true);
  // Drop a client that vanished without closing (out of range, crashed) within a few seconds.
  int value = WIFI_KEEPALIVE_IDLE_S;
  client.setSocketOption(IPPROTO_TCP, TCP_KEEPIDLE, &value, sizeof(value));
  value = WIFI_KEEPALIVE_INTVL_S;
  client.setSocketOption(IPPROTO_TCP, TCP_KEEPINTVL, &value, sizeof(value));
  value = WIFI_KEEPALIVE_COUNT;
  client.setSocketOption(IPPROTO_TCP, TCP_KEEPCNT, &value, sizeof(value));
  openLink(LINK_WIFI);
}

void initCommunication() {
  // The SDK mirrors its console (stdout, so also printf) onto the USB serial endpoint; a log line
  // from the WiFi driver would land in the middle of a binary reply. ROM printf (early and
  // in-interrupt error logs) is routed to UART0 only.
  esp_log_level_set("*", ESP_LOG_NONE);
  g_usb_print = false;
  initSerial();
  serialWaiter = xTaskGetCurrentTaskHandle();
  esp_intr_alloc(ETS_USB_SERIAL_JTAG_INTR_SOURCE, 0, serialRxIsr, NULL, NULL);  // On the calling core

  // Derive a stable, unique ID from the LAST three octets of the factory MAC. getEfuseMac()
  // packs the MAC least-significant-octet first, so its low 24 bits are the OUI (vendor prefix)
  // that is SHARED across boards — using them made every kit report the same ID. The upper three
  // octets (mac[3..5], the NIC-specific part) are unique per chip and match the tail of the MAC
  // shown in the router's client list. Constant across reboots and STA/AP mode.
  uint64_t mac = ESP.getEfuseMac();
  snprintf(deviceId, sizeof(deviceId), "%02X%02X%02X",
           (uint8_t)(mac >> 24), (uint8_t)(mac >> 32), (uint8_t)(mac >> 40));
  hostname = String(MDNS_HOSTNAME) + "-" + deviceId; // etactilekit-A1B2C3

  WiFi.persistent(false);  // The radio restarts at runtime; never write WiFi settings to flash
  WiFi.setAutoReconnect(false);  // The radio task retries and falls back itself
  // Radio always awake: with modem sleep the router holds packets for the kit until its next beacon
  // wake-up, adding up to several hundred ms to replies in station mode.
  WiFi.setSleep(false);
  WiFi.onEvent(onStaDisconnected, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
  WiFi.setHostname(hostname.c_str());
  wifiWanted = true;       // Listen on WiFi until a serial host connects
  xTaskCreatePinnedToCore(wifiRadioTask, "wifi_radio", 6144, NULL, 1, &wifiTask, 0);
}

bool serviceCommunication() {
  sampleHostPresence();
  const TickType_t now = xTaskGetTickCount();
  if (serialOpen && now - serialSeenTick >= pdMS_TO_TICKS(SERIAL_LINK_TIMEOUT_MS)) {
    serialOpen = false;
    serialRefused = false;  // The port was closed; the next open is a new connection
  }

  switch (activeLink) {
    case LINK_SERIAL:
      if (!serialOpen) {
        closeLink();
        return false;
      }
      return serialPoll();

    case LINK_WIFI:
      if (now - wifiPollTick >= pdMS_TO_TICKS(WIFI_POLL_MS)) {
        wifiPollTick = now;
        errno = 0;  // connected() reads errno even when its probe succeeds
        if (!client.connected()) closeLink();
      }
      break;

    case LINK_NONE:
      if (serialOpen && !serialRefused) {
        if (server) server.end();  // Refuse TCP clients
        requestRadio(false);       // Radio off while a serial host owns the board
        openLink(LINK_SERIAL);
        return true;               // The host's first request is usually already waiting
      }
      if (wifiReady && now - wifiPollTick >= pdMS_TO_TICKS(WIFI_POLL_MS)) {
        wifiPollTick = now;
        if (!server) {
          server.begin();
        } else if (server.hasClient()) {
          acceptWifiClient();
        }
      }
      break;
  }

  // A serial host that does not own the board stays refused until it closes the port. Its bytes
  // are discarded so they can never be parsed as commands later.
  if (serialOpen) {
    serialRefused = true;
    drainSerial();
  }
  return false;
}

bool waitForHostData() {
  usb_serial_jtag_ll_ena_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);  // Fires at once if a packet is already waiting
  return ulTaskNotifyTake(pdTRUE, 1) != 0;
}

int isDataAvailable() {
  switch (activeLink) {
    case LINK_SERIAL: return serialRxHead - serialRxTail;
    case LINK_WIFI:   return client.available();
    default:          return 0;
  }
}

byte readInt_8() {
  switch (activeLink) {
    case LINK_SERIAL: return serialRead();
    case LINK_WIFI: {
      const int value = client.read();
      return value < 0 ? 0 : (byte)value;  // A failed read must never parse as a high amplitude
    }
    default:          return 0;
  }
}

uint16_t readInt_16() {
  const byte low = readInt_8();
  return (uint16_t)(low | (readInt_8() << 8)); // Low byte first
}

void writeBytes(const byte* data, size_t len) {
  switch (activeLink) {
    case LINK_SERIAL: serialWrite(data, len); break;
    case LINK_WIFI:   client.write(data, len); break;
    default:          break;
  }
}

void writeInt_8(byte val) {
  writeBytes(&val, 1);
}
