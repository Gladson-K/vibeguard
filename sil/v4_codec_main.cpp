// Host SIL: encode/decode a V4 compact LoRa frame (optionally signed).
#include <cstdio>
#include <cstring>

#include "v3_cli.h"
#include "vg_core/v3/sha256.h"
#include "vg_core/v4/codec.h"

static void print_frame(const vg::LoraFrame &f, bool valid) {
  std::printf(
      "{\"valid\":%s,\"version\":%u,\"flags\":%u,\"device_id\":%u,"
      "\"seq\":%u,\"ts\":%u,\"rms\":%.3f,\"peak\":%.3f,\"crest\":%.2f,"
      "\"kurtosis\":%.2f,\"dom_freq\":%.0f,\"model_score\":%.2f,"
      "\"battery_mv\":%u,\"rssi\":%d}",
      valid ? "true" : "false", unsigned(f.version), unsigned(f.flags),
      f.device_id, f.seq, f.ts, f.rms, f.peak, f.crest, f.kurtosis,
      double(f.dom_freq), f.model_score, unsigned(f.battery_mv), int(f.rssi));
}

int main(int argc, char **argv) {
  const char *decode_hex = vgcli::arg(argc, argv, "--decode-hex");
  const char *key_hex = vgcli::arg(argc, argv, "--key-hex");

  uint8_t key[64];
  size_t key_len = 0;
  if (key_hex && !vg::hex_decode(key_hex, key, sizeof(key), &key_len)) {
    std::printf("{\"valid\":false,\"error\":\"bad key hex\"}\n");
    return 2;
  }

  if (decode_hex) {
    uint8_t buf[vg::kSignedFrameSize];
    size_t len = 0;
    if (!vg::hex_decode(decode_hex, buf, sizeof(buf), &len)) {
      std::printf("{\"valid\":false,\"error\":\"bad frame hex\"}\n");
      return 2;
    }
    if (len != vg::kLoraFrameSize && len != vg::kSignedFrameSize) {
      std::printf("{\"valid\":false,\"error\":\"bad frame length\"}\n");
      return 2;
    }
    vg::LoraFrame f;
    bool ok;
    if (len == vg::kSignedFrameSize) {
      ok = key_hex && vg::signed_decode(buf, key, key_len, f);
    } else {
      uint16_t crc = 0;
      ok = vg::lora_decode(buf, f, &crc);
    }
    if (vgcli::flag(argc, argv, "--corrupt")) {
      buf[14] ^= 0x01;
      uint16_t crc = 0;
      ok = vg::lora_decode(buf, f, &crc);
    }
    print_frame(f, ok);
    std::printf("\n");
    return ok ? 0 : 1;
  }

  vg::LoraFrame f;
  f.device_id = uint32_t(vgcli::iarg(argc, argv, "--device-id", 1));
  f.seq = uint32_t(vgcli::iarg(argc, argv, "--seq", 0));
  f.ts = uint32_t(vgcli::iarg(argc, argv, "--ts", 0));
  f.rms = vgcli::farg(argc, argv, "--rms", 0.12f);
  f.peak = vgcli::farg(argc, argv, "--peak", 0.40f);
  f.crest = vgcli::farg(argc, argv, "--crest", 3.2f);
  f.kurtosis = vgcli::farg(argc, argv, "--kurtosis", 2.9f);
  f.dom_freq = vgcli::farg(argc, argv, "--dom-freq", 25.0f);
  f.model_score = vgcli::farg(argc, argv, "--model-score", 0.08f);
  f.battery_mv = uint16_t(vgcli::iarg(argc, argv, "--battery", 3900));
  f.rssi = int16_t(vgcli::iarg(argc, argv, "--rssi", -72));

  uint8_t out[vg::kSignedFrameSize];
  size_t len;
  if (key_hex) {
    len = vg::signed_encode(f, key, key_len, out);
  } else {
    len = vg::lora_encode(f, out);
  }

  char hex[vg::kSignedFrameSize * 2 + 1];
  vg::hex_encode(out, len, hex);
  std::printf("{\"frame_hex\":\"%s\",\"len\":%u}\n", hex, unsigned(len));
  return 0;
}
