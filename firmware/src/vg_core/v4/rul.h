#pragma once
#include <stddef.h>

// Remaining-useful-life trend from a monotonic health indicator (RMS or
// kurtosis). Linear least-squares slope; days = (threshold - current)/slope.
namespace vg {

struct RulEstimate {
  float slope_per_day = 0;
  float current = 0;
  float rul_days = 0;
  bool valid = false;
};

RulEstimate rul_estimate(const float *values, const float *times_s, size_t n,
                         float threshold, float min_slope_per_s = 1e-9f);

} // namespace vg
