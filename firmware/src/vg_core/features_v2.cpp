#include "features_v2.h"

#include <math.h>
#include <string.h>

#include "dsp.h"

namespace {
const int MAX_N = 8192;

float kurtosis_of(const float *x, int n) {
  float s2 = 0, s4 = 0;
  for (int i = 0; i < n; i++) {
    float d2 = x[i] * x[i];
    s2 += d2;
    s4 += d2 * d2;
  }
  float var = s2 / n;
  if (var <= 1e-12f) return 0.0f;
  return (s4 / n) / (var * var);
}
}  // namespace

void vg_compute_features_v2(const float *x_in, int n, float fs, V2Features *out) {
  static float re[MAX_N];
  static float im[MAX_N];
  static float env[MAX_N];
  static float xs[MAX_N];  // DC-removed time signal (kept for the envelope)

  float mean = 0;
  for (int i = 0; i < n; i++) mean += x_in[i];
  mean /= n;
  for (int i = 0; i < n; i++) {
    re[i] = x_in[i] - mean;
    xs[i] = re[i];
  }

  // time-domain features on the DC-removed signal
  float s2 = 0, s4 = 0, peak = 0;
  for (int i = 0; i < n; i++) {
    float v = re[i];
    float d2 = v * v;
    s2 += d2;
    s4 += d2 * d2;
    if (fabsf(v) > peak) peak = fabsf(v);
  }
  float var = s2 / n;
  out->rms = sqrtf(var);
  out->peak = peak;
  out->crest = out->rms > 1e-9f ? peak / out->rms : 0.0f;
  out->kurtosis = var > 1e-12f ? (s4 / n) / (var * var) : 0.0f;

  // spectrum
  for (int i = 0; i < n; i++) im[i] = 0.0f;
  vg_fft(re, im, n);

  float mag[MAX_N];
  for (int k = 0; k <= n / 2; k++) mag[k] = sqrtf(re[k] * re[k] + im[k] * im[k]);
  mag[0] = 0.0f;

  float num = 0, den = 0;
  for (int k = 1; k <= n / 2; k++) {
    float f = (float)k * fs / n;
    num += f * mag[k];
    den += mag[k];
  }
  out->centroid = den > 1e-12f ? num / den : 0.0f;

  // log-spaced band energies (20 Hz .. fs/2), matching numpy.geomspace
  const float fmin = 20.0f, fmax = fs / 2.0f;
  float edges[VG_V2_BANDS + 1];
  float ratio = fmax / fmin;
  for (int b = 0; b <= VG_V2_BANDS; b++) {
    edges[b] = fmin * powf(ratio, (float)b / VG_V2_BANDS);
  }
  for (int b = 0; b < VG_V2_BANDS; b++) {
    float lo = edges[b], hi = edges[b + 1];
    float energy = 0;
    for (int k = 1; k <= n / 2; k++) {
      float f = (float)k * fs / n;
      bool in = (f >= lo) && (b < VG_V2_BANDS - 1 ? (f < hi) : (f <= hi));
      if (in) energy += mag[k] * mag[k];
    }
    out->bands[b] = logf(energy + 1e-12f);
  }

  // envelope = |x| smoothed by a moving average, then its spectrum
  int w = n / 256;
  if (w < 1) w = 1;
  int pad = w / 2;
  for (int i = 0; i < n; i++) {
    float sum = 0;
    for (int k = 0; k < w; k++) {
      int idx = i + k - pad;
      if (idx >= 0 && idx < n) sum += fabsf(xs[idx]);
    }
    env[i] = sum / w;
  }
  float emean = 0;
  for (int i = 0; i < n; i++) emean += env[i];
  emean /= n;
  for (int i = 0; i < n; i++) env[i] -= emean;

  float es2 = 0;
  for (int i = 0; i < n; i++) es2 += env[i] * env[i];
  out->env_rms = sqrtf(es2 / n);
  out->env_kurt = kurtosis_of(env, n);
  float epeak = 0;
  for (int i = 0; i < n; i++)
    if (fabsf(env[i]) > epeak) epeak = fabsf(env[i]);
  out->env_peak = epeak;

  for (int i = 0; i < n; i++) {
    re[i] = env[i];
    im[i] = 0.0f;
  }
  vg_fft(re, im, n);
  int best = 0;
  float bm = 0;
  for (int k = 1; k <= n / 2; k++) {
    float m = re[k] * re[k] + im[k] * im[k];
    if (m > bm) {
      bm = m;
      best = k;
    }
  }
  out->env_dom = bm > 1e-12f ? (float)best * fs / n : 0.0f;
  out->dom_freq = out->env_dom;

  int idx = 0;
  out->vector[idx++] = out->rms;
  out->vector[idx++] = out->peak;
  out->vector[idx++] = out->crest;
  out->vector[idx++] = out->kurtosis;
  out->vector[idx++] = out->centroid;
  for (int b = 0; b < VG_V2_BANDS; b++) out->vector[idx++] = out->bands[b];
  out->vector[idx++] = out->env_rms;
  out->vector[idx++] = out->env_peak;
  out->vector[idx++] = out->env_kurt;
  out->vector[idx++] = out->env_dom;
}
