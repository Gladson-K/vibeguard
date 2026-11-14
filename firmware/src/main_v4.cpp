// VibeGuard V4 firmware: LoRa fleet node. Sensing/inference reuse the V2 ADXL
// and TinyML path; signed 32-byte frames go over SX1262 with an ESP-NOW
// fallback. V3 OTA, provisioning, power and rollback are retained.
#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <time.h>

#include "adxl.h"
#include "config.h"
#include "v4/continual.h"
#include "v4/lora.h"
#include "v4/security.h"
#include "v4/v4_config.h"
#include "v3/ota.h"
#include "v3/power.h"
#include "v3/provisioning.h"
#include "v3/wifi_fast.h"
#include "vg_core/features_v2.h"
#include "vg_core/model.h"
#include "vg_core/model_data.h"
#include "vg_core/v4/codec.h"
#include "vg_core/v4/rollout.h"

static float buf[WINDOW_N_V2];
static ContinualState continual;

static String device_id() {
  Preferences prefs;
  prefs.begin("vgwifi", true);
  String id = prefs.getString("device_id", DEVICE_ID);
  prefs.end();
  return id;
}

static uint16_t battery_mv() {
  return uint16_t(analogReadMilliVolts(PIN_BATTERY_ADC) * 2);
}

static void sample_window() {
  const uint32_t period_us = 1000000UL / FS_HZ_V2;
  uint32_t next = micros();
  for (int i = 0; i < WINDOW_N_V2; i++) {
    while ((int32_t)(micros() - next) < 0) {
    }
    next += period_us;
    float m = 1.0f;
    if (!adxl_read_g(m)) m = buf[i ? i - 1 : 0];
    buf[i] = m;
  }
}

static vg::LoraFrame make_frame(const V2Features &f, float score, bool drift,
                                bool espnow, uint16_t mv) {
  vg::LoraFrame fr;
  fr.version = 4;
  fr.flags = uint8_t((drift ? 0x01 : 0) | (mv < VG_BATTERY_LOW_MV ? 0x02 : 0) |
                     (espnow ? 0x04 : 0));
  String id = device_id();
  fr.device_id = vg::fnv1a32(id.c_str());
  fr.seq = security_next_seq();
  time_t now = time(nullptr);
  fr.ts = (now > 1700000000) ? uint32_t(now) : uint32_t(millis() / 1000);
  fr.rms = f.rms;
  fr.peak = f.peak;
  fr.crest = f.crest;
  fr.kurtosis = f.kurtosis;
  fr.dom_freq = f.dom_freq;
  fr.model_score = score;
  fr.battery_mv = mv;
  fr.rssi = 0;
  return fr;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_STATUS, OUTPUT);
  pinMode(PIN_BUTTON_PROV, INPUT_PULLUP);
  power_begin();
  security_begin();
  continual_begin(&continual);
  if (!lora_begin()) Serial.println("LoRa init failed");

  if (ota_boot_pending()) {
    if (adxl_begin(PIN_ADXL_CS) && adxl_self_test()) {
      ota_confirm_boot();
    } else {
      Serial.println("new image failed self-test; rolling back");
      ota_rollback();
    }
  }

  if (!wifi_credentials_saved() || digitalRead(PIN_BUTTON_PROV) == LOW) {
    provisioning_start();
    return;
  }

  bool online = wifi_fast_connect(VG_WIFI_TIMEOUT_MS);
  if (online) {
    espnow_begin();
    if (power_boot_count() % VG_OTA_EVERY_BOOTS == 0) {
      String err;
      if (ota_perform(VG_OTA_MANIFEST_URL, VG_OTA_FIRMWARE_URL, VG_DEVICE_KEY_HEX,
                      VG_FW_VERSION, err)) {
        ESP.restart();
      }
      Serial.printf("OTA skipped: %s\n", err.c_str());
    }
  }

  if (!adxl_begin(PIN_ADXL_CS)) {
    Serial.println("sensor init failed");
    power_deep_sleep(VG_SLEEP_S);
  }

  sample_window();
  V2Features f;
  vg_compute_features_v2(buf, WINDOW_N_V2, FS_HZ_V2, &f);
  float score = vg_model_score(VG_MODEL, f.vector);
  bool drift = continual_update(&continual, f.rms);
  uint16_t mv = battery_mv();

  vg::LoraFrame fr = make_frame(f, score, drift, online && espnow_active(), mv);
  uint8_t key[64];
  size_t key_len = security_key(key, sizeof(key));
  bool sent = lora_send_frame(fr, key, key_len);

  Serial.printf("rms=%.4f score=%.5f drift=%d battery=%umV sent=%d\n", f.rms,
                score, drift ? 1 : 0, unsigned(mv), sent ? 1 : 0);
  digitalWrite(PIN_LED_STATUS, sent ? HIGH : LOW);
  delay(50);
  digitalWrite(PIN_LED_STATUS, LOW);
  power_deep_sleep(VG_SLEEP_S);
}

void loop() {
  if (provisioning_active()) {
    provisioning_loop();
    delay(10);
  }
}
