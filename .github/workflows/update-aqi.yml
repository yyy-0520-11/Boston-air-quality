// Boston air quality map box (ESP32)
// - 16 neighborhood LEDs from aqi.json (EPA AirNow, updated hourly by GitHub)
// - The neighborhood where the box sits uses the box's own PMS5003 PM2.5 sensor
// - 3 legend LEDs: Dangerous (blue), Poor (yellow), Safe (green)
//
// Libraries: Adafruit NeoPixel, ArduinoJson, Adafruit PM25 AQI Sensor
// Wiring:
//   LED string: 5V -> VIN, GND -> GND, DIN -> GPIO 16
//   PMS5003 adapter: VCC -> VIN, GND -> GND, TX -> GPIO 25 (SET, RESET, RX unconnected)

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_PM25AQI.h>

// ====== Change these ======
const char* WIFI_SSID = "your-wifi-name";
const char* WIFI_PASS = "your-wifi-password";
const char* DATA_URL  = "https://yyy-0520-11.github.io/Boston-air-quality/aqi.json";
const char* LOCAL_NAME = "Roxbury";   // neighborhood where the box is displayed
// ==========================

const unsigned long WEB_UPDATE_MS    = 10UL * 60 * 1000;  // every 10 minutes
const unsigned long SENSOR_UPDATE_MS = 30UL * 1000;       // every 30 seconds

#define LED_PIN    16
#define PMS_RX_PIN 25
#define MAP_LEDS   16
#define TOTAL_LEDS 19

Adafruit_NeoPixel leds(TOTAL_LEDS, LED_PIN, NEO_RGB + NEO_KHZ800);
Adafruit_PM25AQI pms;

// Neighborhood names in LED-string order; must match aqi.json exactly.
// aqi.json has 20 names (same as the website map); pick the 16 on the box:
// Allston, Brighton, Back Bay, Beacon Hill, Charlestown, Chinatown, Dorchester,
// Downtown, East Boston, Fenway, Hyde Park, Jamaica Plain, Mattapan, Mission Hill,
// North End, Roslindale, Roxbury, South Boston, South End, West Roxbury
const char* NAMES[MAP_LEDS] = {
  "Allston", "Back Bay", "Charlestown", "Chinatown",
  "Dorchester", "Downtown", "East Boston", "Fenway",
  "Hyde Park", "Jamaica Plain", "Mattapan", "Roslindale",
  "Roxbury", "South Boston", "South End", "West Roxbury"
};

int localIndex = -1;
bool sensorOk = false;
float pmSum = 0;
int pmCount = 0;
unsigned long lastWebUpdate = 0;
unsigned long lastSensorUpdate = 0;

uint32_t colorForAQI(int aqi) {
  if (aqi <= 50)  return leds.Color(0, 255, 0);    // Safe: green
  if (aqi <= 100) return leds.Color(255, 160, 0);  // Poor: yellow
  return leds.Color(0, 0, 255);                    // Dangerous: blue
}

// PM2.5 (ug/m3) -> AQI, EPA breakpoints (2024)
int pm25ToAQI(float pm) {
  const float cLow[]  = {0.0, 9.1, 35.5, 55.5, 125.5, 225.5};
  const float cHigh[] = {9.0, 35.4, 55.4, 125.4, 225.4, 325.4};
  const int   iLow[]  = {0, 51, 101, 151, 201, 301};
  const int   iHigh[] = {50, 100, 150, 200, 300, 500};
  pm = floor(pm * 10) / 10;  // EPA truncates to one decimal
  for (int i = 0; i < 6; i++) {
    if (pm <= cHigh[i]) {
      return round((iHigh[i] - iLow[i]) / (cHigh[i] - cLow[i]) * (pm - cLow[i]) + iLow[i]);
    }
  }
  return 500;
}

void fetchWebData() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    return;
  }
  WiFiClientSecure client;
  client.setInsecure();  // school project: skip certificate check
  HTTPClient http;
  http.begin(client, DATA_URL);

  int code = http.GET();
  if (code == 200) {
    JsonDocument doc;
    if (!deserializeJson(doc, http.getString())) {
      JsonObject data = doc["neighborhoods"];
      for (int i = 0; i < MAP_LEDS; i++) {
        if (i == localIndex && sensorOk) continue;  // own sensor wins
        if (data[NAMES[i]].is<int>()) {
          leds.setPixelColor(i, colorForAQI(data[NAMES[i]]));
        } else {
          leds.setPixelColor(i, leds.Color(20, 20, 20));  // no data: dim white
        }
      }
      leds.show();
      Serial.println("Web data updated");
    }
  } else {
    Serial.printf("Web fetch failed, code %d\n", code);
  }
  http.end();
}

void readSensor() {
  PM25_AQI_Data reading;
  if (pms.read(&reading)) {
    pmSum += reading.pm25_env;
    pmCount++;
  }
}

void showSensor() {
  if (pmCount == 0 || localIndex < 0) return;
  float pmAvg = pmSum / pmCount;
  int aqi = pm25ToAQI(pmAvg);
  pmSum = 0;
  pmCount = 0;
  sensorOk = true;
  leds.setPixelColor(localIndex, colorForAQI(aqi));
  leds.show();
  Serial.printf("Own sensor: PM2.5 %.1f ug/m3, AQI %d\n", pmAvg, aqi);
}

void setup() {
  Serial.begin(115200);

  leds.begin();
  leds.setBrightness(80);
  leds.clear();
  leds.setPixelColor(16, leds.Color(0, 0, 255));    // legend: Dangerous
  leds.setPixelColor(17, leds.Color(255, 160, 0));  // legend: Poor
  leds.setPixelColor(18, leds.Color(0, 255, 0));    // legend: Safe
  leds.show();

  for (int i = 0; i < MAP_LEDS; i++) {
    if (strcmp(NAMES[i], LOCAL_NAME) == 0) localIndex = i;
  }

  Serial2.begin(9600, SERIAL_8N1, PMS_RX_PIN, -1);
  delay(3000);  // let the sensor fan start
  if (!pms.begin_UART(&Serial2)) {
    Serial.println("PMS5003 not found; using web data only");
  }

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(" connected");

  fetchWebData();
  lastWebUpdate = millis();
  lastSensorUpdate = millis();
}

void loop() {
  readSensor();

  if (millis() - lastSensorUpdate > SENSOR_UPDATE_MS) {
    showSensor();
    lastSensorUpdate = millis();
  }
  if (millis() - lastWebUpdate > WEB_UPDATE_MS) {
    fetchWebData();
    lastWebUpdate = millis();
  }
  delay(1000);
}
