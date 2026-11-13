#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"
#include "vg_features_v1.h"

#define MPU_ADDR 0x68
static float buf[WINDOW_N], im[WINDOW_N];
WiFiClient net;
PubSubClient mqtt(net);

static void mpu_write(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.write(val); Wire.endTransmission();
}
static bool mpu_read_g(float &mag) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x3B); Wire.endTransmission(false);
  if (Wire.requestFrom(MPU_ADDR, 6) != 6) return false;
  int16_t ax = (Wire.read() << 8) | Wire.read();
  int16_t ay = (Wire.read() << 8) | Wire.read();
  int16_t az = (Wire.read() << 8) | Wire.read();
  const float s = 1.0f / 4096.0f;        // +-8g range
  mag = sqrtf((ax * s) * (ax * s) + (ay * s) * (ay * s) + (az * s) * (az * s));
  return true;
}
static void wifi_connect() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
}
static void send(const Features &f) {
  JsonDocument d;
  d["device_id"] = DEVICE_ID; d["fs"] = FS_HZ;
  d["rms"] = f.rms; d["peak"] = f.peak; d["crest"] = f.crest;
  d["kurtosis"] = f.kurt; d["dom_freq"] = f.dom_freq;
  String body; serializeJson(d, body);
#if USE_MQTT
  mqtt.setServer(GATEWAY_HOST, MQTT_PORT);
  if (!mqtt.connected()) mqtt.connect(DEVICE_ID);
  mqtt.publish("vibeguard/" DEVICE_ID "/features", body.c_str());
  mqtt.loop();
#else
  HTTPClient http;
  http.begin(String("http://") + GATEWAY_HOST + ":" + GATEWAY_PORT + "/api/ingest");
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  Serial.printf("POST %d\n", code);
  http.end();
#endif
}

void setup() {
  Serial.begin(115200);
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  mpu_write(0x6B, 0x00);   // wake
  mpu_write(0x1C, 0x10);   // +-8g
  mpu_write(0x1A, 0x01);   // DLPF 188 Hz, keeps content below Nyquist (500 Hz) reasonable
  wifi_connect();
}

void loop() {
  const uint32_t period_us = 1000000UL / FS_HZ;
  uint32_t next = micros();
  for (int i = 0; i < WINDOW_N; i++) {
    while ((int32_t)(micros() - next) < 0) {}
    next += period_us;
    float m = 1.0f;
    if (!mpu_read_g(m)) m = buf[i ? i - 1 : 0];
    buf[i] = m;
  }
  Features f = compute_features(buf, im, WINDOW_N, FS_HZ);
  Serial.printf("rms=%.4f peak=%.3f crest=%.2f kurt=%.2f f=%.1fHz\n", f.rms, f.peak, f.crest, f.kurt, f.dom_freq);
  wifi_connect();
  if (WiFi.status() == WL_CONNECTED) send(f);
}
