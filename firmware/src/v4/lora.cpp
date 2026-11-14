#include "lora.h"

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>

#include "sx1262.h"
#include "v4_config.h"

static Sx1262 radio;
static bool lora_ready = false;
static bool espnow_ready = false;
static uint8_t broadcast_mac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

bool lora_begin() {
  lora_ready = radio.begin(SPI, PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI,
                           PIN_LORA_CS, PIN_LORA_RESET, PIN_LORA_BUSY,
                           PIN_LORA_DIO1);
  if (!lora_ready) return false;
  lora_ready = radio.configure(VG_LORA_FREQ_MHZ, VG_LORA_SF, VG_LORA_BW,
                               VG_LORA_CR, VG_LORA_PREAMBLE, VG_LORA_TX_DBM,
                               VG_LORA_SYNC_WORD);
  return lora_ready;
}

bool lora_send_frame(const vg::LoraFrame &frame, const uint8_t *key,
                     size_t key_len) {
  uint8_t buf[vg::kSignedFrameSize];
  size_t len = key && key_len ? vg::signed_encode(frame, key, key_len, buf)
                              : vg::lora_encode(frame, buf);
  if (lora_ready && radio.transmit(buf, len)) return true;
  return espnow_send(buf, len);
}

int lora_receive_frame(vg::LoraFrame &frame, const uint8_t *key,
                       size_t key_len, uint32_t timeout_ms) {
  if (!lora_ready) return -1;
  uint8_t buf[vg::kSignedFrameSize];
  int len = radio.receive(buf, sizeof(buf), timeout_ms);
  if (len <= 0) return len;
  if (len == int(vg::kSignedFrameSize)) {
    if (!key || !key_len) return -2;
    return vg::signed_decode(buf, key, key_len, frame) ? len : -2;
  }
  if (len == int(vg::kLoraFrameSize)) return vg::lora_decode(buf, frame) ? len : -3;
  return -3;
}

bool espnow_begin() {
  if (espnow_ready) return true;
  if (WiFi.status() != WL_CONNECTED && WiFi.getMode() == WIFI_MODE_NULL)
    return false;
  if (esp_now_init() != ESP_OK) return false;
  esp_now_peer_info_t peer = {};
  for (int i = 0; i < 6; i++) peer.peer_addr[i] = broadcast_mac[i];
  peer.channel = 1;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
  espnow_ready = true;
  return true;
}

bool espnow_send(const uint8_t *data, size_t len) {
  if (!espnow_ready && !espnow_begin()) return false;
  return esp_now_send(broadcast_mac, data, len) == ESP_OK;
}

bool espnow_active() { return espnow_ready; }
