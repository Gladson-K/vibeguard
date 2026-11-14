#pragma once
#include <Arduino.h>

// Deep-sleep helpers. The duty-cycle decision logic lives in
// vg_core/v3/state_machine.cpp; this file only wraps the ESP32 sleep call.
void power_begin();
uint32_t power_boot_count();
void power_deep_sleep(uint32_t seconds);
