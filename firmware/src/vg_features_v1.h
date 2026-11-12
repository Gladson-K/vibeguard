#pragma once
#include <math.h>
#include <stdint.h>
// Mirrors gateway/features.py. x: acceleration magnitude in g, length n (power of 2).
struct Features { float rms, peak, crest, kurt, dom_freq; };

static void fft_inplace(float *re, float *im, int n) {
  for (int i = 1, j = 0; i < n; i++) {
    int bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { float t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
  }
  for (int len = 2; len <= n; len <<= 1) {
    float ang = -2.0f * M_PI / len;
    float wr = cosf(ang), wi = sinf(ang);
    for (int i = 0; i < n; i += len) {
      float cr = 1, ci = 0;
      for (int k = 0; k < len / 2; k++) {
        int a = i + k, b = i + k + len / 2;
        float tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti;
        re[a] += tr; im[a] += ti;
        float ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

static Features compute_features(float *x, float *im, int n, float fs) {
  float mean = 0;
  for (int i = 0; i < n; i++) mean += x[i];
  mean /= n;
  float s2 = 0, s4 = 0, peak = 0;
  for (int i = 0; i < n; i++) {
    x[i] -= mean;                       // remove gravity/DC
    float d2 = x[i] * x[i];
    s2 += d2; s4 += d2 * d2;
    if (fabsf(x[i]) > peak) peak = fabsf(x[i]);
  }
  float var = s2 / n;
  Features f;
  f.rms = sqrtf(var);
  f.peak = peak;
  f.crest = f.rms > 1e-9f ? peak / f.rms : 0;
  f.kurt = var > 1e-12f ? (s4 / n) / (var * var) : 0;
  for (int i = 0; i < n; i++) im[i] = 0;
  fft_inplace(x, im, n);
  int best = 1; float bm = 0;
  for (int k = 1; k < n / 2; k++) {
    float m = x[k] * x[k] + im[k] * im[k];
    if (m > bm) { bm = m; best = k; }
  }
  f.dom_freq = best * fs / n;
  return f;
}
