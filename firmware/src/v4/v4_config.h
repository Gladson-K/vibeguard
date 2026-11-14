#pragma once

// V4 LoRa fleet-node configuration. Board constants only; portable policy
// (codec/rollout/drift/diagnosis/RUL) lives in vg_core/v4.
#define VG_FW_VERSION 4
#define VG_MIN_VERSION 3
#define VG_WIFI_TIMEOUT_MS 8000
#define VG_OTA_EVERY_BOOTS 96

#define VG_OTA_MANIFEST_URL "https://ota.vibeguard.local/manifest.json"
#define VG_OTA_FIRMWARE_URL "https://ota.vibeguard.local/firmware.bin"

#define PIN_LED_STATUS 2
#define PIN_BUTTON_PROV 0
#define PIN_BATTERY_ADC 3

// SX1262 on the ESP32-S3 SPI bus.
#define PIN_LORA_SCK 12
#define PIN_LORA_MISO 13
#define PIN_LORA_MOSI 11
#define PIN_LORA_CS 14
#define PIN_LORA_RESET 15
#define PIN_LORA_BUSY 16
#define PIN_LORA_DIO1 17

#define VG_LORA_FREQ_MHZ 868.0f
#define VG_LORA_SF 7
#define VG_LORA_BW 125.0f // kHz
#define VG_LORA_CR 5     // 4/5
#define VG_LORA_PREAMBLE 8
#define VG_LORA_TX_DBM 14
#define VG_LORA_SYNC_WORD 0x12
#define VG_LORA_QUEUE_DEPTH 4

// Battery reporting / low-power policy (inherits the V3 duty cycle).
#define VG_SLEEP_S 45
#define VG_BATTERY_MAH 2000.0f
#define VG_TARGET_MA 15.0f
#define VG_TARGET_DAYS 30.0f
#define VG_BATTERY_LOW_MV 3300

// Per-device keys are provisioned to NVS at the factory. The test key is only
// a fallback for bench units; production provisioning must overwrite it.
#define VG_DEVICE_KEY_HEX                                                  \
  "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"

// Continual-learning shadow baseline.
#define VG_DRIFT_WINDOW 32
#define VG_DRIFT_INTERVAL 16
#define VG_DRIFT_PSI_THRESHOLD 0.2f
#define VG_DRIFT_ALPHA 0.05f
