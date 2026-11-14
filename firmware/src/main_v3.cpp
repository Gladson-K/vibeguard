// VibeGuard V3 firmware: battery node with signed OTA, SoftAP provisioning,
// fast Wi-Fi reconnect and a deep-sleep duty cycle. Sensing/inference reuse the
// V2 ADXL path and portable vg_core.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>

#include "adxl.h"
#include "config.h"
#include "v3/v3_config.h"
#include "v3/ota.h"
#include "v3/power.h"
#include "v3/prodtest.h"
#include "v3/provisioning.h"
#include "v3/wifi_fast.h"
#include "vg_core/features_v2.h"
#include "vg_core/model.h"
#include "vg_core/model_data.h"
#include "vg_core/v3/power_model.h"

static float buf[WINDOW_N_V2];

static String device_id() {
  Preferences prefs;
  prefs.begin("vgwifi", true);
  String id = prefs.getString("device_id", DEVICE_ID);
  prefs.end();
  return id;
}

static void publish(const V2Features &f, float score, const String &id) {
  JsonDocument d;
  d["device_id"] = id;
  d["fs"] = FS_HZ_V2;
  d["sensor"] = adxl_chip_name();
  d["rms"] = f.rms;
  d["peak"] = f.peak;
  d["crest"] = f.crest;
  d["kurtosis"] = f.kurtosis;
  d["dom_freq"] = f.dom_freq;
  d["model_score"] = score;
  d["model_version"] = VG_MODEL.version;
  d["firmware"] = VG_FW_VERSION;
  String body;
  serializeJson(d, body);

  HTTPClient http;
  http.begin(String("http://") + GATEWAY_HOST + ":" + GATEWAY_PORT +
             "/api/ingest");
  http.addHeader("Content-Type", "application/json");
  int code = http.POST(body);
  Serial.printf("POST %d\n", code);
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON_PROV, INPUT_PULLUP);
  pinMode(PIN_LED_STATUS, OUTPUT);
  power_begin();

#ifdef VG_PRODTEST
  vg::ProdTestResult r = prodtest_run("factory");
  prodtest_store_device_id("factory");
  Serial.printf("PRODTEST %s\n", r.label);
  while (true) delay(1000);
#endif

  // A newly flashed image boots as PENDING_VERIFY; only confirm it if the
  // hardware self-test passes, otherwise switch back to the previous slot.
  if (ota_boot_pending()) {
    if (adxl_begin(PIN_ADXL_CS) && adxl_self_test()) {
      ota_confirm_boot();
    } else {
      Serial.println("new image failed self-test; rolling back");
      ota_rollback();
    }
  }

  if (!wifi_credentials_saved() || digitalRead(PIN_BUTTON_PROV) == LOW) {
    Serial.println("starting provisioning portal");
    provisioning_start();
    return;
  }

  if (power_boot_count() % VG_OTA_EVERY_BOOTS == 0) {
    String err;
    if (ota_perform(VG_OTA_MANIFEST_URL, VG_OTA_FIRMWARE_URL, VG_OTA_KEY_HEX,
                    VG_FW_VERSION, err)) {
      Serial.println("OTA applied; rebooting");
      ESP.restart();
    }
    Serial.printf("OTA skipped: %s\n", err.c_str());
  }

  if (!adxl_begin(PIN_ADXL_CS)) {
    Serial.println("sensor init failed");
    power_deep_sleep(VG_SLEEP_S);
  }

  bool online = wifi_fast_connect(VG_WIFI_TIMEOUT_MS);

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

  V2Features f;
  vg_compute_features_v2(buf, WINDOW_N_V2, FS_HZ_V2, &f);
  float score = vg_model_score(VG_MODEL, f.vector);

  vg::PowerProfile profile;
  vg::PowerEstimate pe = vg::power_estimate(profile, VG_BATTERY_MAH,
                                            VG_TARGET_MA, VG_TARGET_DAYS);
  Serial.printf("rms=%.4f score=%.5f avg=%.3f mA days=%.1f online=%d\n", f.rms,
                score, pe.avg_ma, pe.battery_days, online ? 1 : 0);

  if (online) {
    digitalWrite(PIN_LED_STATUS, HIGH);
    publish(f, score, device_id());
    digitalWrite(PIN_LED_STATUS, LOW);
  }

  power_deep_sleep(VG_SLEEP_S);
}

void loop() {
  if (provisioning_active()) {
    provisioning_loop();
    delay(10);
  }
}
