#pragma once

// Duty-cycle power budget for the V3 battery node. Kept portable so the same
// numbers can be checked in CI (host SIL) and on the device bench.
namespace vg {

struct PowerProfile {
  float idle_ma = 12.0f;   // sensor sampling / MCU awake
  float idle_ms = 1000.0f; // 1 s measurement window
  float infer_ma = 20.0f;  // spectral features + int8 inference
  float infer_ms = 50.0f;
  float tx_ma = 80.0f; // Wi-Fi/MQTT burst
  float tx_ms = 100.0f;
  float sleep_ma = 0.02f; // deep sleep
  float sleep_s = 45.0f;  // 30-60 s duty cycle target
};

struct PowerEstimate {
  float avg_ma;
  float battery_days;
  bool meets_current;  // avg_ma <= target_ma
  bool meets_battery;  // battery_days >= target_days
};

PowerEstimate power_estimate(const PowerProfile &p, float battery_mah,
                             float target_ma = 15.0f,
                             float target_days = 30.0f);

} // namespace vg
