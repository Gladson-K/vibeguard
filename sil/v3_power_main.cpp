// Host SIL: evaluate the V3 duty-cycle power budget.
#include <cstdio>

#include "vg_core/v3/power_model.h"
#include "v3_cli.h"

int main(int argc, char **argv) {
  vg::PowerProfile p;
  p.idle_ma = vgcli::farg(argc, argv, "--idle-ma", p.idle_ma);
  p.idle_ms = vgcli::farg(argc, argv, "--idle-ms", p.idle_ms);
  p.infer_ma = vgcli::farg(argc, argv, "--infer-ma", p.infer_ma);
  p.infer_ms = vgcli::farg(argc, argv, "--infer-ms", p.infer_ms);
  p.tx_ma = vgcli::farg(argc, argv, "--tx-ma", p.tx_ma);
  p.tx_ms = vgcli::farg(argc, argv, "--tx-ms", p.tx_ms);
  p.sleep_ma = vgcli::farg(argc, argv, "--sleep-ma", p.sleep_ma);
  p.sleep_s = vgcli::farg(argc, argv, "--sleep-s", p.sleep_s);

  float battery = vgcli::farg(argc, argv, "--battery-mah", 2000.0f);
  float target_ma = vgcli::farg(argc, argv, "--target-ma", 15.0f);
  float target_days = vgcli::farg(argc, argv, "--target-days", 30.0f);

  vg::PowerEstimate e = vg::power_estimate(p, battery, target_ma, target_days);
  std::printf(
      "{\"avg_ma\":%.4f,\"battery_days\":%.2f,\"meets_current\":%s,"
      "\"meets_battery\":%s}\n",
      e.avg_ma, e.battery_days, e.meets_current ? "true" : "false",
      e.meets_battery ? "true" : "false");
  return e.meets_current && e.meets_battery ? 0 : 1;
}
