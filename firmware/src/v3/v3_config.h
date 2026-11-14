#pragma once

// V3 battery-node configuration. The portable policy lives in vg_core/v3;
// this header only holds board and deployment constants.

#define VG_FW_VERSION 3
#define VG_MIN_VERSION 3
#define VG_SLEEP_S 45
#define VG_BATTERY_MAH 2000.0f
#define VG_TARGET_MA 15.0f
#define VG_TARGET_DAYS 30.0f
#define VG_WIFI_TIMEOUT_MS 8000
#define VG_OTA_EVERY_BOOTS 96 // roughly once a day at a 45 s duty cycle

#define VG_OTA_MANIFEST_URL "https://ota.vibeguard.local/manifest.json"
#define VG_OTA_FIRMWARE_URL "https://ota.vibeguard.local/firmware.bin"
// Per-device key, provisioned at the factory and stored in NVS. Tests use a
// fixed key; production units must override this.
#define VG_OTA_KEY_HEX                                                     \
  "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"

#define PIN_LED_STATUS 2
#define PIN_BUTTON_PROV 0
#define PIN_RAIL_3V3_ADC 1
#define PIN_RAIL_1V8_ADC 2
#define PIN_BATTERY_ADC 3
