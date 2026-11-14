#include "sha256.h"

#include <cstring>

namespace vg {
namespace {

constexpr uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

inline uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
inline uint32_t ch(uint32_t x, uint32_t y, uint32_t z) {
  return (x & y) ^ (~x & z);
}
inline uint32_t maj(uint32_t x, uint32_t y, uint32_t z) {
  return (x & y) ^ (x & z) ^ (y & z);
}
inline uint32_t bsig0(uint32_t x) {
  return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22);
}
inline uint32_t bsig1(uint32_t x) {
  return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25);
}
inline uint32_t ssig0(uint32_t x) {
  return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3);
}
inline uint32_t ssig1(uint32_t x) {
  return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10);
}

struct Ctx {
  uint32_t h[8];
  uint64_t bits;
  uint8_t buf[64];
  size_t n;
};

void init(Ctx &c) {
  c.h[0] = 0x6a09e667;
  c.h[1] = 0xbb67ae85;
  c.h[2] = 0x3c6ef372;
  c.h[3] = 0xa54ff53a;
  c.h[4] = 0x510e527f;
  c.h[5] = 0x9b05688c;
  c.h[6] = 0x1f83d9ab;
  c.h[7] = 0x5be0cd19;
  c.bits = 0;
  c.n = 0;
}

void block(Ctx &c, const uint8_t *p) {
  uint32_t w[64];
  for (int i = 0; i < 16; i++) {
    w[i] = (uint32_t(p[i * 4]) << 24) | (uint32_t(p[i * 4 + 1]) << 16) |
           (uint32_t(p[i * 4 + 2]) << 8) | uint32_t(p[i * 4 + 3]);
  }
  for (int i = 16; i < 64; i++)
    w[i] = ssig1(w[i - 2]) + w[i - 7] + ssig0(w[i - 15]) + w[i - 16];

  uint32_t a = c.h[0], b = c.h[1], cc = c.h[2], d = c.h[3];
  uint32_t e = c.h[4], f = c.h[5], g = c.h[6], h = c.h[7];
  for (int i = 0; i < 64; i++) {
    uint32_t t1 = h + bsig1(e) + ch(e, f, g) + K[i] + w[i];
    uint32_t t2 = bsig0(a) + maj(a, b, cc);
    h = g;
    g = f;
    f = e;
    e = d + t1;
    d = cc;
    cc = b;
    b = a;
    a = t1 + t2;
  }
  c.h[0] += a;
  c.h[1] += b;
  c.h[2] += cc;
  c.h[3] += d;
  c.h[4] += e;
  c.h[5] += f;
  c.h[6] += g;
  c.h[7] += h;
}

void update(Ctx &c, const uint8_t *data, size_t len) {
  c.bits += uint64_t(len) * 8;
  while (len) {
    size_t take = 64 - c.n;
    if (take > len) take = len;
    std::memcpy(c.buf + c.n, data, take);
    c.n += take;
    data += take;
    len -= take;
    if (c.n == 64) {
      block(c, c.buf);
      c.n = 0;
    }
  }
}

void finish(Ctx &c, uint8_t out[32]) {
  uint64_t bits = c.bits;
  uint8_t tmp[64];
  if (c.n) std::memcpy(tmp, c.buf, c.n);
  size_t idx = c.n;
  tmp[idx++] = 0x80;
  if (idx > 56) {
    std::memset(tmp + idx, 0, 64 - idx);
    block(c, tmp);
    idx = 0;
  }
  std::memset(tmp + idx, 0, 56 - idx);
  for (int i = 0; i < 8; i++) tmp[56 + i] = uint8_t((bits >> (56 - 8 * i)) & 0xff);
  block(c, tmp);
  for (int i = 0; i < 8; i++) {
    out[i * 4] = uint8_t(c.h[i] >> 24);
    out[i * 4 + 1] = uint8_t(c.h[i] >> 16);
    out[i * 4 + 2] = uint8_t(c.h[i] >> 8);
    out[i * 4 + 3] = uint8_t(c.h[i]);
  }
}

} // namespace

void sha256(const void *data, size_t len, uint8_t out[32]) {
  Ctx c;
  init(c);
  update(c, static_cast<const uint8_t *>(data), len);
  finish(c, out);
}

void hmac_sha256(const uint8_t *key, size_t key_len, const uint8_t *msg,
                 size_t msg_len, uint8_t out[32]) {
  uint8_t k[64];
  std::memset(k, 0, sizeof(k));
  if (key_len > 64) {
    sha256(key, key_len, k);
  } else if (key_len) {
    std::memcpy(k, key, key_len);
  }
  uint8_t ipad[64], opad[64];
  for (int i = 0; i < 64; i++) {
    ipad[i] = uint8_t(k[i] ^ 0x36);
    opad[i] = uint8_t(k[i] ^ 0x5c);
  }
  Ctx c;
  uint8_t inner[32];
  init(c);
  update(c, ipad, 64);
  update(c, msg, msg_len);
  finish(c, inner);
  init(c);
  update(c, opad, 64);
  update(c, inner, 32);
  finish(c, out);
}

bool hex_decode(const char *hex, uint8_t *out, size_t cap, size_t *out_len) {
  if (!hex) return false;
  size_t n = std::strlen(hex);
  if (n % 2) return false;
  size_t m = n / 2;
  if (m > cap) return false;
  auto val = [](char c) -> int {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
  };
  for (size_t i = 0; i < m; i++) {
    int hi = val(hex[2 * i]);
    int lo = val(hex[2 * i + 1]);
    if (hi < 0 || lo < 0) return false;
    out[i] = uint8_t((hi << 4) | lo);
  }
  if (out_len) *out_len = m;
  return true;
}

void hex_encode(const uint8_t *in, size_t len, char *out) {
  static const char *d = "0123456789abcdef";
  for (size_t i = 0; i < len; i++) {
    out[2 * i] = d[in[i] >> 4];
    out[2 * i + 1] = d[in[i] & 0x0f];
  }
  out[2 * len] = '\0';
}

bool ct_equal(const uint8_t *a, const uint8_t *b, size_t len) {
  uint8_t diff = 0;
  for (size_t i = 0; i < len; i++) diff = uint8_t(diff | (a[i] ^ b[i]));
  return diff == 0;
}

} // namespace vg
