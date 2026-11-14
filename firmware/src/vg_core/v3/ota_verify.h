#pragma once
#include <stddef.h>
#include <stdint.h>

// Signed-OTA policy shared by the ESP32 firmware and the host verifier.
// The manifest signature is HMAC-SHA256 over a canonical, newline-delimited
// string (see ota_canonical). Keeping this in vg_core means the exact same
// policy is exercised by Docker tests and on the device.
namespace vg {

enum class OtaResult {
  Ok = 0,
  BadSignature,
  BadHash,
  BadSize,
  Downgrade,
  TooOld,
};

const char *ota_result_name(OtaResult r);

// Writes the canonical signed payload and returns its length (excluding NUL).
// Format: "vg-ota-v1\n<version>\n<min_version>\n<size>\n<sha256_hex>\n"
size_t ota_canonical(char *out, size_t cap, uint32_t version,
                     uint32_t min_version, uint32_t size,
                     const char *sha256_hex);

OtaResult ota_verify(uint32_t current_version, uint32_t version,
                     uint32_t min_version, uint32_t size,
                     const char *sha256_hex, const char *sig_hex,
                     const void *firmware, size_t firmware_len,
                     const void *key, size_t key_len);

} // namespace vg
