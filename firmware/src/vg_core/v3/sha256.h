#pragma once
#include <stddef.h>
#include <stdint.h>

// Portable SHA-256 / HMAC-SHA256 + hex helpers used by V3 signed OTA.
// No Arduino dependency: the same code runs on device and in host SIL builds.
namespace vg {

void sha256(const void *data, size_t len, uint8_t out[32]);
void hmac_sha256(const uint8_t *key, size_t key_len, const uint8_t *msg,
                 size_t msg_len, uint8_t out[32]);

// Decode lowercase/uppercase hex. Returns false on odd length, bad char or
// if the decoded size exceeds `cap`.
bool hex_decode(const char *hex, uint8_t *out, size_t cap, size_t *out_len);

// Writes 2*len lowercase hex chars plus a NUL terminator.
void hex_encode(const uint8_t *in, size_t len, char *out);

// Constant-time comparison (avoids leaking signature prefix match timing).
bool ct_equal(const uint8_t *a, const uint8_t *b, size_t len);

} // namespace vg
