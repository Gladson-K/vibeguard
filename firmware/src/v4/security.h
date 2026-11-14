#pragma once
#include <stddef.h>
#include <stdint.h>

#include "vg_core/v4/codec.h"

// Per-device identity: 32-byte key in NVS, monotonic sequence number and
// signed-frame helpers. The key never leaves the device.
bool security_begin();
size_t security_key(uint8_t *out, size_t cap);
bool security_set_key_hex(const char *hex);
uint32_t security_next_seq();
uint32_t security_last_seq();
bool security_sign_frame(const vg::LoraFrame &frame,
                         uint8_t out[vg::kSignedFrameSize]);
