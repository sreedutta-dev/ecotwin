
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Wi-Fi credentials
const char* WIFI_SSID = "WIFI_NAME";
const char* WIFI_PASSWORD = "WIFI_PASSWORD";

// Replace with your computer's IPv4 address
const char* SERVER_URL =
  "http://192.168.1.105:5000/api/sensors/readings";

// ESP32 analog pins
const int SOIL_PIN = 34;   // YL-69 module AO
const int LIGHT_PIN = 35;  // LDR module AO

const unsigned long SEND_INTERVAL = 5000;
unsigned long lastSendTime = 0;

// Adjust these after testing your YL-69 sensor.
// Many capacitive and resistive sensors have different raw ranges.
const int SOIL_DRY = 3500;
const int SOIL_WET = 1200;

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

int readSoilMoisture() {
  int raw = analogRead(SOIL_PIN);

  // Common calibration pattern: higher raw = drier soil.
  // Reverse the mapping if your sensor behaves differently.
  int percent = map(raw, SOIL_DRY, SOIL_WET, 0, 100);

  return constrain(percent, 0, 100);
}

int readLightLevel() {
  int raw = analogRead(LIGHT_PIN);

  Serial.print("Raw LDR ADC: ");
  Serial.println(raw);

  // Temporary value only; we will calibrate it next.
  return raw;
}

void sendSensorData() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected. Reconnecting...");
    connectWiFi();
  }

  int soilMoisture = readSoilMoisture();
  int lightLevel = readLightLevel();

  JsonDocument json;
  json["Soil Moisture"] = soilMoisture;
  json["Light"] = lightLevel;

  String payload;
  serializeJson(json, payload);

  Serial.println("\nSending JSON:");
  Serial.println(payload);

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  int responseCode = http.POST(payload);

  Serial.print("HTTP response code: ");
  Serial.println(responseCode);

  if (responseCode > 0) {
    Serial.println(http.getString());
  } else {
    Serial.println("Could not reach Flask API.");
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);  // ESP32: readings from 0 to 4095

  connectWiFi();
}

void loop() {
  unsigned long now = millis();

  if (now - lastSendTime >= SEND_INTERVAL) {
    lastSendTime = now;
    sendSensorData();
  }
}
