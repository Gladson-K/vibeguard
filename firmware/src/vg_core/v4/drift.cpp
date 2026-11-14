#include "drift.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace vg {

DriftReport drift_report(const float *reference, size_t n_ref,
                         const float *current, size_t n_cur, int bins,
                         float psi_threshold, float alpha) {
  DriftReport out;
  if (!reference || !current || n_ref == 0 || n_cur == 0 || bins < 1) return out;

  float lo = reference[0], hi = reference[0];
  for (size_t i = 1; i < n_ref; i++) {
    lo = std::min(lo, reference[i]);
    hi = std::max(hi, reference[i]);
  }
  for (size_t i = 0; i < n_cur; i++) {
    lo = std::min(lo, current[i]);
    hi = std::max(hi, current[i]);
  }
  const float width = hi - lo;

  std::vector<double> rc(size_t(bins), 0.0), cc(size_t(bins), 0.0);
  auto bin_of = [&](float v) {
    if (width <= 0.0f) return 0;
    int b = int((v - lo) / width * float(bins));
    if (b < 0) b = 0;
    if (b >= bins) b = bins - 1;
    return b;
  };
  for (size_t i = 0; i < n_ref; i++) rc[size_t(bin_of(reference[i]))] += 1.0;
  for (size_t i = 0; i < n_cur; i++) cc[size_t(bin_of(current[i]))] += 1.0;

  const double eps = 1e-6;
  double psi = 0.0;
  for (int b = 0; b < bins; b++) {
    double p = rc[size_t(b)] / double(n_ref);
    double q = cc[size_t(b)] / double(n_cur);
    if (p < eps) p = eps;
    if (q < eps) q = eps;
    psi += (q - p) * std::log(q / p);
  }

  std::vector<float> a(reference, reference + n_ref);
  std::vector<float> b(current, current + n_cur);
  std::sort(a.begin(), a.end());
  std::sort(b.begin(), b.end());
  size_t i = 0, j = 0;
  double d = 0.0;
  while (i < n_ref || j < n_cur) {
    float v = (j >= n_cur || (i < n_ref && a[i] <= b[j])) ? a[i] : b[j];
    while (i < n_ref && a[i] <= v) i++;
    while (j < n_cur && b[j] <= v) j++;
    d = std::max(d, std::fabs(double(i) / double(n_ref) -
                               double(j) / double(n_cur)));
  }

  double ne = double(n_ref) * double(n_cur) / double(n_ref + n_cur);
  double lambda = (std::sqrt(ne) + 0.12 + 0.11 / std::sqrt(ne)) * d;
  double pvalue = 1.0;
  if (lambda > 0.0) {
    pvalue = 0.0;
    for (int k = 1; k <= 100; k++) {
      double term = 2.0 * ((k % 2) ? 1.0 : -1.0) *
                    std::exp(-2.0 * double(k * k) * lambda * lambda);
      pvalue += term;
    }
    pvalue = std::min(1.0, std::max(0.0, pvalue));
  }

  out.psi = float(psi);
  out.ks = float(d);
  out.ks_pvalue = float(pvalue);
  out.drift = out.psi >= psi_threshold || out.ks_pvalue < alpha;
  return out;
}

} // namespace vg
