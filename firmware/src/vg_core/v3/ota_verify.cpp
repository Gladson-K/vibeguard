#include "ota_verify.h"

#include <cstdio>
#include <cstring>

#include "sha256.h"

namespace vg {

const char *ota_result_name(OtaResult r) {
  switch (r) {
  case OtaResult::Ok:
    return "ok";
  case OtaResult::BadSignature:
    return "bad_signature";
  case OtaResult::BadHash:
    return "bad_hash";
  case OtaResult::BadSize:
    return "bad_size";
  case OtaResult::Downgrade:
    return "downgrade";
  case OtaResult::TooOld:
    return "too_old";
  }
  return "unknown";
}

size_t ota_canonical(char *out, size_t cap, uint32_t version,
                     uint32_t min_version, uint32_t size,
                     const char *sha256_hex) {
  if (!sha256_hex) sha256_hex = "";
  int n = std::snprintf(out, cap, "vg-ota-v1\n%u\n%u\n%u\n%s\n", version,
                        min_version, size, sha256_hex);
  return n < 0 ? 0 : size_t(n);
}

OtaResult ota_verify(uint32_t current_version, uint32_t version,
                     uint32_t min_version, uint32_t size,
                     const char *sha256_hex, const char *sig_hex,
                     const void *firmware, size_t firmware_len,
                     const void *key, size_t key_len) {
  if (firmware_len != size) return OtaResult::BadSize;

  if (!sig_hex || std::strlen(sig_hex) != 64) return OtaResult::BadSignature;
  uint8_t sig[32];
  size_t sig_len = 0;
  if (!hex_decode(sig_hex, sig, sizeof(sig), &sig_len) || sig_len != 32)
    return OtaResult::BadSignature;

  if (!sha256_hex || std::strlen(sha256_hex) != 64) return OtaResult::BadHash;
  uint8_t want_hash[32];
  size_t hash_len = 0;
  if (!hex_decode(sha256_hex, want_hash, sizeof(want_hash), &hash_len) ||
      hash_len != 32)
    return OtaResult::BadHash;

  char canonical[160];
  size_t clen = ota_canonical(canonical, sizeof(canonical), version,
                              min_version, size, sha256_hex);
  if (clen == 0 || clen >= sizeof(canonical)) return OtaResult::BadSignature;

  uint8_t mac[32];
  hmac_sha256(static_cast<const uint8_t *>(key), key_len,
              reinterpret_cast<const uint8_t *>(canonical), clen, mac);
  if (!ct_equal(mac, sig, sizeof(mac))) return OtaResult::BadSignature;

  uint8_t got_hash[32];
  sha256(firmware, firmware_len, got_hash);
  if (!ct_equal(got_hash, want_hash, sizeof(got_hash))) return OtaResult::BadHash;

  if (version <= current_version) return OtaResult::Downgrade;
  if (version < min_version) return OtaResult::TooOld;

  return OtaResult::Ok;
}

} // namespace vg
