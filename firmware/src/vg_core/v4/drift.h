#pragma once
#include <stddef.h>

// Distribution-shift detector for continual learning: PSI + two-sample KS.
// Used in shadow mode on the device and by the gateway drift endpoint.
namespace vg {

struct DriftReport {
  float psi = 0;
  float ks = 0;
  float ks_pvalue = 1;
  bool drift = false;
};

DriftReport drift_report(const float *reference, size_t n_ref,
                         const float *current, size_t n_cur, int bins = 10,
                         float psi_threshold = 0.2f, float alpha = 0.05f);

} // namespace vg
