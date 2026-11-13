// VibeGuard V2 firmware: ADXL345/ADXL355 SPI @ 3.2 kHz, spectral features,
// int8 TinyML autoencoder score, HTTP/MQTT publish.
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "adxl.h"
#include "vg_core/features_v2.h"
#include "vg_core/model.h"
#include "vg_core/model_data.h"

static float buf[WINDOW_N_V2];
static WiFiClient net;
static PubSubClient mqtt(net);

static void wifi_connect() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
}

static void send(const V2Features &f, float score) {
  JsonDocument d;
  d["device_id"] = DEVICE_ID;
  d["fs"] = FS_HZ_V2;
  d["sensor"] = adxl_chip_name();
  d["rms"] = f.rms;
  d["peak"] = f.peak;
  d["crest"] = f.crest;
  d["kurtosis"] = f.kurtosis;
  d["dom_freq"] = f.dom_freq;
  d["model_score"] = score;
  d["model_version"] = VG_MODEL.version;
  String body;
  serializeJson(d, body);
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
  if (!adxl_begin(PIN_ADXL_CS)) Serial.println("ADXL not found");
  else Serial.printf("ADXL: %s\n", adxl_chip_name());
  wifi_connect();
}

void loop() {
  const uint32_t period_us = 1000000UL / FS_HZ_V2;
  uint32_t next = micros();
  for (int i = 0; i < WINDOW_N_V2; i++) {
    while ((int32_t)(micros() - next) < 0) {}
    next += period_us;
    float m = 1.0f;
    if (!adxl_read_g(m)) m = buf[i ? i - 1 : 0];
    buf[i] = m;
  }
  V2Features f;
  vg_compute_features_v2(buf, WINDOW_N_V2, FS_HZ_V2, &f);
  float score = vg_model_score(VG_MODEL, f.vector);
  Serial.printf("rms=%.4f crest=%.2f kurt=%.2f score=%.5f\n", f.rms, f.crest, f.kurtosis, score);
  wifi_connect();
  if (WiFi.status() == WL_CONNECTED) send(f, score);
}
