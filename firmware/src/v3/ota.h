#pragma once
#include <Arduino.h>

// Signed OTA update with HMAC-SHA256 manifest authentication and rollback.
// The verification policy itself lives in vg_core/v3/ota_verify.cpp and is
// covered by host tests; this layer only does HTTP, flash and rollback.

bool ota_perform(const char *manifest_url, const char *firmware_url,
                 const char *key_hex, uint32_t current_version, String &err);

// Rollback support: after an OTA the new image boots in PENDING_VERIFY.
// Confirm it only after the runtime self-test passes, otherwise switch back.
bool ota_boot_pending();
void ota_confirm_boot();
void ota_rollback();
