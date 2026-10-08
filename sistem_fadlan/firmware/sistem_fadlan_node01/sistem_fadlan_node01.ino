  # =============================================================================
# firmware/sistem_fadlan_node01.ino — Firmware ESP32 sensor node
# PMS5003 (UART2) + MQ-135 (ADC) + BME280 (I2C) → publish MQTT tiap 30 detik
# Sesuai PRD Section 13 (FR-IOT-01 s/d FR-IOT-08)
#
# Library Arduino IDE yang dibutuhkan (Tahap 3):
#   - Adafruit BME280 Library (+ Adafruit Unified Sensor)
#   - ArduinoJson (v6/v7)
#   - PubSubClient (MQTT)
#   - ESP32 board package (Boards Manager)
# =============================================================================

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <HardwareSerial.h>

// ----------------- KONFIGURASI — UBAH 3 BARIS SEBELUM UPLOAD -----------------
// 1) WIFI_SSID     : nama WiFi/hotspot yang SAMA dengan laptop
// 2) WIFI_PASSWORD : password WiFi/hotspot itu
// 3) MQTT_BROKER   : IP laptop (cek via "ipconfig" -> IPv4 Address)
const char* WIFI_SSID     = "FadlanNurul";
const char* WIFI_PASSWORD = "234000234";

// MQTT broker = IP laptop yang menjalankan Flask (bukan "localhost"!)
const char* MQTT_BROKER   = "172.20.10.3";
const int   MQTT_PORT     = 1883;
const char* MQTT_TOPIC    = "air_quality/node01";
const char* CLIENT_ID     = "esp32_node01";

const unsigned long SEND_INTERVAL_MS = 30000UL;  // 30 detik (PRD final)

// ----------------- PIN (wiring PRD Section 13.1) -----------------
#define PMS_RX_PIN   16   // ESP32 RX2 <- TX PMS5003
#define PMS_TX_PIN   17   // ESP32 TX2 -> RX PMS5003
#define MQ135_PIN    34   // ADC1_CH6 (input-only)
#define BME_SDA      21
#define BME_SCL      22

// ----------------- OBJEK -----------------
HardwareSerial pmsSerial(2);
Adafruit_BME280 bme;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastSend = 0;

// ----------------- NTP (FR-IOT-05) -----------------
struct tm timeinfo;
bool getNTPTime(char* buf, size_t len) {
  if (!getLocalTime(&timeinfo, 500)) {
    return false;  // caller pakai fallback millis
  }
  strftime(buf, len, "%Y-%m-%dT%H:%M:%S", &timeinfo);
  return true;
}

// ----------------- WIFI + MQTT (FR-IOT-06/08) -----------------
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[wifi] Menghubungkan");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.print(" OK, IP: ");
  Serial.println(WiFi.localIP());
}

void setupMQTT() {
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setKeepAlive(60);
  mqtt.setBufferSize(512);  // payload JSON + header MQTT aman
}

bool ensureMQTT() {
  if (mqtt.connected()) return true;
  Serial.print("[mqtt] Menghubungkan broker...");
  // retry 1s → 5s → 10s (PRD 17.4)
  static int attempt = 0;
  int delayMs = attempt == 0 ? 1000 : (attempt == 1 ? 5000 : 10000);
  if (mqtt.connect(CLIENT_ID)) {
    attempt = 0;
    Serial.println(" OK");
    return true;
  }
  attempt = min(attempt + 1, 2);
  Serial.print(" gagal (rc="); Serial.print(mqtt.state()); Serial.println(")");
  delay(delayMs);
  return false;
}

// ----------------- PMS5003 (FR-IOT-01) -----------------
// Frame PMS5003 = 32 byte (datasheet Plantower, bagian atmosferic):
//   byte 0-1   : header 0x42 0x4D
//   byte 10-11 : PM1.0  ug/m3
//   byte 12-13 : PM2.5  ug/m3
//   byte 14-15 : PM10   ug/m3
//   byte 30-31 : checksum = jumlah byte 0..29 (mod 65536)
bool readPMS(float &pm1, float &pm25, float &pm10) {
  uint8_t buf[32];
  unsigned long start = millis();
  while (millis() - start < 2000) {  // timeout 2 detik (PRD 17.4)
    if (pmsSerial.available() >= 32 &&
        pmsSerial.peek() == 0x42) {
      pmsSerial.readBytes(buf, 32);
      if (buf[0] == 0x42 && buf[1] == 0x4D) {
        // Validasi checksum — frame rusak dibuang (PRD 17.1)
        uint16_t sum = 0;
        for (int i = 0; i < 30; i++) sum += buf[i];
        uint16_t chk = ((uint16_t)buf[30] << 8) | buf[31];
        if (sum != chk) {
          Serial.println("[pms] Checksum salah — frame dibuang");
          return false;
        }
        pm1  = ((uint16_t)buf[10] << 8) | buf[11];
        pm25 = ((uint16_t)buf[12] << 8) | buf[13];
        pm10 = ((uint16_t)buf[14] << 8) | buf[15];
        return true;
      }
    }
    delay(10);
  }
  return false;  // skip iterasi ini (PRD 17.4)
}

// ----------------- SETUP -----------------
void setup() {
  Serial.begin(115200);

  pmsSerial.begin(9600, SERIAL_8N1, PMS_RX_PIN, PMS_TX_PIN);
  Wire.begin(BME_SDA, BME_SCL);

  // BME280: gagal deteksi → kirim -1 sebagai flag (PRD 17.4)
  if (!bme.begin(0x76)) {
    Serial.println("[bme280] ERROR: sensor tidak terdeteksi di I2C (0x76/0x77)!");
    Serial.println("[bme280] Sistem lanjut — nilai cuaca dikirim -1");
  }

  pinMode(MQ135_PIN, INPUT);
  analogSetAttenuation(ADC_11db);  // ADC full-range ~3.3V

  setupWiFi();
  configTime(8 * 3600, 0, "pool.ntp.org");  // WITA (Palu) = UTC+8
  setupMQTT();
}

// ----------------- LOOP -----------------
void loop() {
  // Reconnect Wi-Fi jika putus
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[wifi] Terputus — reconnect...");
    setupWiFi();
  }
  ensureMQTT();
  mqtt.loop();

  if (millis() - lastSend < SEND_INTERVAL_MS) return;
  lastSend = millis();

  // 1. Baca PMS5003 (PM1.0 + PM2.5 + PM10)
  float pm1 = 0, pm25 = 0, pm10 = 0;
  bool pmsOk = readPMS(pm1, pm25, pm10);
  if (!pmsOk) {
    Serial.println("[pms] Timeout — skip iterasi ini");
    return;
  }

  // 2. Baca BME280 (flag -1 jika mati)
  float temperature, humidity, pressure;
  if (bme.readTemperature() > -100) {  // sensor hidup
    temperature = bme.readTemperature();
    humidity    = bme.readHumidity();
    pressure    = bme.readPressure() / 100.0F;  // Pa → hPa
  } else {
    temperature = -1; humidity = -1; pressure = -1;
  }

  // 3. Baca MQ-135 (FR-IOT-03)
  int gasRaw = analogRead(MQ135_PIN);

  // 4. Timestamp NTP, fallback millis (PRD 17.4)
  char ts[24] = "";
  if (!getNTPTime(ts, sizeof(ts))) {
    snprintf(ts, sizeof(ts), "%lu", millis() / 1000);  // fallback tak-ISO
  }

  // 5. Kemas JSON payload (PRD Section 13.3)
  StaticJsonDocument<256> doc;   // ArduinoJson v6; pakai JsonDocument untuk v7
  doc["node_id"]     = "node01";
  doc["timestamp"]   = ts;
  doc["pm1_0"]       = pm1;
  doc["pm25"]        = pm25;
  doc["pm10"]        = pm10;
  doc["gas_raw"]     = gasRaw;
  doc["temperature"] = temperature;
  doc["humidity"]    = humidity;
  doc["pressure"]    = pressure;

  char payload[256];
  serializeJson(doc, payload);

  // 6. Publish QoS 1 (FR-IOT-07)
  if (mqtt.publish(MQTT_TOPIC, payload, false, 1)) {
    Serial.print("[mqtt] Terkirim: ");
    Serial.println(payload);
  } else {
    Serial.println("[mqtt] Publish gagal");
  }
}
