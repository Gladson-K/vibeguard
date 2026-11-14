#include "rul.h"

#include <cmath>

namespace vg {

RulEstimate rul_estimate(const float *values, const float *times_s, size_t n,
                         float threshold, float min_slope_per_s) {
  RulEstimate e;
  if (!values || !times_s || n < 3) return e;

  double t_mean = 0, v_mean = 0;
  for (size_t i = 0; i < n; i++) {
    t_mean += times_s[i];
    v_mean += values[i];
  }
  t_mean /= double(n);
  v_mean /= double(n);

  double num = 0, den = 0;
  for (size_t i = 0; i < n; i++) {
    double dt = times_s[i] - t_mean;
    num += dt * (values[i] - v_mean);
    den += dt * dt;
  }
  if (den <= 0.0) return e;

  double slope = num / den; // units per second
  e.current = values[n - 1];
  e.slope_per_day = float(slope * 86400.0);
  if (slope <= double(min_slope_per_s)) return e;

  double days = (threshold - e.current) / (slope * 86400.0);
  if (days < 0.0) days = 0.0;
  e.rul_days = float(days);
  e.valid = true;
  return e;
}

} // namespace vg
