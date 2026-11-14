#include "ota.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Update.h>
#include <esp_heap_caps.h>
#include <esp_ota_ops.h>

#include "vg_core/v3/ota_verify.h"
#include "vg_core/v3/sha256.h"

static bool download(HTTPClient &http, uint8_t *dst, size_t size) {
  WiFiClient *stream = http.getStreamPtr();
  size_t got = 0;
  uint32_t last = millis();
  while (got < size && (millis() - last) < 15000) {
    size_t want = size - got;
    if (want > 4096) want = 4096;
    size_t n = stream->readBytes(dst + got, want);
    if (n) {
      got += n;
      last = millis();
    } else {
      delay(1);
    }
  }
  return got == size;
}

bool ota_perform(const char *manifest_url, const char *firmware_url,
                 const char *key_hex, uint32_t current_version, String &err) {
  HTTPClient http;
  if (!http.begin(manifest_url)) {
    err = "manifest begin failed";
    return false;
  }
  int code = http.GET();
  if (code != 200) {
    err = "manifest HTTP " + String(code);
    http.end();
    return false;
  }
  String body = http.getString();
  http.end();

  JsonDocument doc;
  if (deserializeJson(doc, body)) {
    err = "manifest json";
    return false;
  }
  uint32_t version = doc["version"] | 0;
  uint32_t min_version = doc["min_version"] | 0;
  uint32_t size = doc["size"] | 0;
  const char *sha = doc["sha256"] | "";
  const char *sig = doc["sig"] | "";
  if (!version || !size || !*sha || !*sig) {
    err = "manifest fields";
    return false;
  }

  uint8_t key[64];
  size_t key_len = 0;
  if (!vg::hex_decode(key_hex, key, sizeof(key), &key_len)) {
    err = "bad key";
    return false;
  }

  uint8_t *fw = psramFound() ? static_cast<uint8_t *>(ps_malloc(size))
                             : static_cast<uint8_t *>(malloc(size));
  if (!fw) {
    err = "no memory";
    return false;
  }

  if (!http.begin(firmware_url)) {
    free(fw);
    err = "firmware begin failed";
    return false;
  }
  code = http.GET();
  if (code != 200 || !download(http, fw, size)) {
    http.end();
    free(fw);
    err = "firmware download " + String(code);
    return false;
  }
  http.end();

  vg::OtaResult r =
      vg::ota_verify(current_version, version, min_version, size, sha, sig, fw,
                     size, key, key_len);
  if (r != vg::OtaResult::Ok) {
    free(fw);
    err = String("verify: ") + vg::ota_result_name(r);
    return false;
  }

  bool ok = Update.begin(size) && Update.write(fw, size) == size &&
            Update.end(true);
  free(fw);
  if (!ok) {
    err = "flash failed";
    return false;
  }
  err = "reboot";
  return true;
}

bool ota_boot_pending() {
  const esp_partition_t *running = esp_ota_get_running_partition();
  esp_ota_img_states_t state;
  return esp_ota_get_state_partition(running, &state) == ESP_OK &&
         state == ESP_OTA_IMG_PENDING_VERIFY;
}

void ota_confirm_boot() { esp_ota_mark_app_valid_cancel_rollback(); }

void ota_rollback() {
  const esp_partition_t *other = esp_ota_get_next_update_partition(nullptr);
  if (other) {
    esp_ota_set_boot_partition(other);
    delay(100);
    esp_restart();
  }
}
