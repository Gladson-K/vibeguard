#include "security.h"

#include <Preferences.h>

#include "v4_config.h"
#include "vg_core/v3/sha256.h"

static Preferences prefs;
static uint8_t device_key[64];
static size_t device_key_len = 0;
static uint32_t seq_counter = 0;
static bool began = false;

bool security_begin() {
  if (began) return true;
  if (!prefs.begin("vgsec", false)) return false;
  String hex = prefs.getString("key", "");
  if (hex.isEmpty()) {
    hex = VG_DEVICE_KEY_HEX;
    prefs.putString("key", hex);
  }
  device_key_len = 0;
  if (!vg::hex_decode(hex.c_str(), device_key, sizeof(device_key),
                      &device_key_len)) {
    prefs.end();
    return false;
  }
  seq_counter = prefs.getUInt("seq", 0);
  began = true;
  return true;
}

size_t security_key(uint8_t *out, size_t cap) {
  if (!began && !security_begin()) return 0;
  if (device_key_len > cap) return 0;
  for (size_t i = 0; i < device_key_len; i++) out[i] = device_key[i];
  return device_key_len;
}

bool security_set_key_hex(const char *hex) {
  if (!began && !security_begin()) return false;
  size_t len = 0;
  if (!vg::hex_decode(hex, device_key, sizeof(device_key), &len)) return false;
  if (len < 16) return false;
  device_key_len = len;
  prefs.putString("key", hex);
  return true;
}

uint32_t security_next_seq() {
  if (!began && !security_begin()) return 0;
  seq_counter++;
  prefs.putUInt("seq", seq_counter);
  return seq_counter;
}

uint32_t security_last_seq() { return seq_counter; }

bool security_sign_frame(const vg::LoraFrame &frame,
                         uint8_t out[vg::kSignedFrameSize]) {
  size_t len = security_key(device_key, sizeof(device_key));
  if (!len) return false;
  vg::signed_encode(frame, device_key, len, out);
  return true;
}
