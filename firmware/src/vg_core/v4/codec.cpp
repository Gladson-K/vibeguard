#include "codec.h"

#include <cmath>
#include <cstring>

#include "../v3/sha256.h"

namespace vg {
namespace {

void put16(uint8_t *p, uint16_t v) {
  p[0] = uint8_t(v & 0xff);
  p[1] = uint8_t((v >> 8) & 0xff);
}
void put32(uint8_t *p, uint32_t v) {
  p[0] = uint8_t(v & 0xff);
  p[1] = uint8_t((v >> 8) & 0xff);
  p[2] = uint8_t((v >> 16) & 0xff);
  p[3] = uint8_t((v >> 24) & 0xff);
}
uint16_t get16(const uint8_t *p) {
  return uint16_t(p[0]) | uint16_t(uint16_t(p[1]) << 8);
}
uint32_t get32(const uint8_t *p) {
  return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) |
         (uint32_t(p[3]) << 24);
}
uint16_t scale_u16(float v, float scale) {
  if (!std::isfinite(v) || v < 0.0f) v = 0.0f;
  float x = v * scale;
  if (x > 65535.0f) x = 65535.0f;
  return uint16_t(std::lround(x));
}

} // namespace

uint16_t crc16_ccitt(const uint8_t *data, size_t len, uint16_t init) {
  uint16_t crc = init;
  for (size_t i = 0; i < len; i++) {
    crc ^= uint16_t(data[i]) << 8;
    for (int b = 0; b < 8; b++)
      crc = (crc & 0x8000) ? uint16_t((crc << 1) ^ 0x1021) : uint16_t(crc << 1);
  }
  return crc;
}

size_t lora_encode(const LoraFrame &f, uint8_t out[kLoraFrameSize]) {
  std::memset(out, 0, kLoraFrameSize);
  out[0] = f.version ? f.version : 1;
  out[1] = f.flags;
  put32(out + 2, f.device_id);
  put32(out + 6, f.seq);
  put32(out + 10, f.ts);
  put16(out + 14, scale_u16(f.rms, 1000.0f));
  put16(out + 16, scale_u16(f.peak, 1000.0f));
  put16(out + 18, scale_u16(f.crest, 100.0f));
  put16(out + 20, scale_u16(f.kurtosis, 100.0f));
  put16(out + 22, scale_u16(f.dom_freq, 1.0f));
  put16(out + 24, scale_u16(f.model_score, 100.0f));
  put16(out + 26, f.battery_mv);
  put16(out + 28, uint16_t(f.rssi));
  put16(out + 30, crc16_ccitt(out, 30));
  return kLoraFrameSize;
}

bool lora_decode(const uint8_t in[kLoraFrameSize], LoraFrame &f,
                 uint16_t *crc_got) {
  uint16_t calc = crc16_ccitt(in, 30);
  uint16_t got = get16(in + 30);
  if (crc_got) *crc_got = got;
  if (calc != got) return false;
  f.version = in[0];
  f.flags = in[1];
  f.device_id = get32(in + 2);
  f.seq = get32(in + 6);
  f.ts = get32(in + 10);
  f.rms = get16(in + 14) / 1000.0f;
  f.peak = get16(in + 16) / 1000.0f;
  f.crest = get16(in + 18) / 100.0f;
  f.kurtosis = get16(in + 20) / 100.0f;
  f.dom_freq = float(get16(in + 22));
  f.model_score = get16(in + 24) / 100.0f;
  f.battery_mv = get16(in + 26);
  f.rssi = int16_t(get16(in + 28));
  return true;
}

size_t signed_encode(const LoraFrame &frame, const uint8_t *key, size_t key_len,
                     uint8_t out[kSignedFrameSize]) {
  lora_encode(frame, out);
  uint8_t mac[32];
  hmac_sha256(key, key_len, out, kLoraFrameSize, mac);
  std::memcpy(out + kLoraFrameSize, mac, 8);
  return kSignedFrameSize;
}

bool signed_decode(const uint8_t in[kSignedFrameSize], const uint8_t *key,
                   size_t key_len, LoraFrame &frame) {
  uint8_t mac[32];
  hmac_sha256(key, key_len, in, kLoraFrameSize, mac);
  if (!ct_equal(mac, in + kLoraFrameSize, 8)) return false;
  return lora_decode(in, frame);
}

} // namespace vg
