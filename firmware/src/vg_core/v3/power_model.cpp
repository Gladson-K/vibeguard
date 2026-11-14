#include "power_model.h"

namespace vg {

PowerEstimate power_estimate(const PowerProfile &p, float battery_mah,
                             float target_ma, float target_days) {
  PowerEstimate e{0.0f, 0.0f, false, false};

  float sleep_ms = p.sleep_s * 1000.0f;
  float period_ms = p.idle_ms + p.infer_ms + p.tx_ms + sleep_ms;
  if (period_ms <= 0.0f) return e;

  float charge_ma_ms = p.idle_ma * p.idle_ms + p.infer_ma * p.infer_ms +
                       p.tx_ma * p.tx_ms + p.sleep_ma * sleep_ms;
  e.avg_ma = charge_ma_ms / period_ms;
  e.battery_days = e.avg_ma > 0.0f ? battery_mah / e.avg_ma / 24.0f : 1.0e9f;
  e.meets_current = e.avg_ma <= target_ma;
  e.meets_battery = e.battery_days >= target_days;
  return e;
}

} // namespace vg
