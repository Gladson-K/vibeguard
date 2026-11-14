#pragma once
#include <stddef.h>
#include <stdint.h>

#include "vg_core/v4/codec.h"

// High-level fleet transport: SX1262 LoRa primary, ESP-NOW fallback when the
// node is already associated to Wi-Fi (for example during an OTA window).
bool lora_begin();
bool lora_send_frame(const vg::LoraFrame &frame, const uint8_t *key,
                     size_t key_len);
int lora_receive_frame(vg::LoraFrame &frame, const uint8_t *key,
                       size_t key_len, uint32_t timeout_ms);

bool espnow_begin();
bool espnow_send(const uint8_t *data, size_t len);
bool espnow_active();
