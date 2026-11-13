#pragma once

// V2 spectral feature extraction. Portable (no Arduino deps) so it can run on
// device and in the host software-in-the-loop harness. Mirrors harness/features_v2.py.
#define VG_V2_BANDS 15
#define VG_V2_DIM (5 + VG_V2_BANDS + 4)  // 24

struct V2Features {
  float rms;
  float peak;
  float crest;
  float kurtosis;
  float centroid;
  float bands[VG_V2_BANDS];
  float env_rms;
  float env_peak;
  float env_kurt;
  float env_dom;
  float dom_freq;              // alias of env_dom (gateway field)
  float vector[VG_V2_DIM];
};

// x: acceleration magnitude in g, length n (power of two). fs in Hz.
void vg_compute_features_v2(const float *x, int n, float fs, V2Features *out);
