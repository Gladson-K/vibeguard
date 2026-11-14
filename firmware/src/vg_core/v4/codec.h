#pragma once
#include <stddef.h>
#include <stdint.h>

// V4 LoRa telemetry codec. A compact 32-byte frame carries one feature window
// (no raw samples). An optional 8-byte truncated HMAC-SHA256 turns it into a
// 40-byte authenticated frame. The same layout is implemented by
// gateway/codec.py and covered by parity tests.
namespace vg {

constexpr size_t kLoraFrameSize = 32;
constexpr size_t kSignedFrameSize = 40;

struct LoraFrame {
  uint8_t version = 1;
  uint8_t flags = 0;
  uint32_t device_id = 0;
  uint32_t seq = 0;
  uint32_t ts = 0;
  float rms = 0;
  float peak = 0;
  float crest = 0;
  float kurtosis = 0;
  float dom_freq = 0;
  float model_score = 0;
  uint16_t battery_mv = 0;
  int16_t rssi = 0;
};

uint16_t crc16_ccitt(const uint8_t *data, size_t len, uint16_t init = 0xFFFF);
size_t lora_encode(const LoraFrame &frame, uint8_t out[kLoraFrameSize]);
bool lora_decode(const uint8_t in[kLoraFrameSize], LoraFrame &frame,
                 uint16_t *crc_got = nullptr);

size_t signed_encode(const LoraFrame &frame, const uint8_t *key, size_t key_len,
                     uint8_t out[kSignedFrameSize]);
bool signed_decode(const uint8_t in[kSignedFrameSize], const uint8_t *key,
                   size_t key_len, LoraFrame &frame);

} // namespace vg
