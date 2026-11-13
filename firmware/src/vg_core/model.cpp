#include "model.h"

#include <math.h>
#include <stddef.h>

namespace {
const int VG_MAX_DIM = 128;
float buf_a[VG_MAX_DIM];
float buf_b[VG_MAX_DIM];
int8_t qbuf[VG_MAX_DIM];

inline int8_t q8(float v, float scale) {
  if (scale <= 1e-12f) return 0;
  long r = lroundf(v / scale);
  if (r > 127) r = 127;
  if (r < -127) r = -127;
  return (int8_t)r;
}
}  // namespace

float vg_model_score(const QModel &m, const float *feature) {
  float *cur = buf_a;
  float *nxt = buf_b;

  for (int i = 0; i < m.in_dim; i++) {
    cur[i] = (feature[i] - m.input_mean[i]) / m.input_std[i];
  }

  float in_scale = m.layers[0].in_scale;
  for (int i = 0; i < m.in_dim; i++) qbuf[i] = q8(cur[i], in_scale);

  for (int l = 0; l < m.n_layers; l++) {
    const QLayer &L = m.layers[l];
    for (int o = 0; o < L.out_dim; o++) {
      const int8_t *wrow = L.w + (size_t)o * L.in_dim;
      int32_t acc = 0;
      for (int i = 0; i < L.in_dim; i++) acc += (int32_t)wrow[i] * (int32_t)qbuf[i];
      float y = (float)acc * (L.w_scale * L.in_scale) + L.b[o];
      if (L.act == VG_ACT_TANH) y = tanhf(y);
      else if (L.act == VG_ACT_RELU) y = y > 0 ? y : 0;
      nxt[o] = y;
    }
    if (l + 1 < m.n_layers) {
      for (int o = 0; o < L.out_dim; o++) qbuf[o] = q8(nxt[o], L.out_scale);
    }
    float *t = cur;
    cur = nxt;
    nxt = t;
  }

  float err = 0;
  for (int i = 0; i < m.in_dim; i++) {
    float xn = (feature[i] - m.input_mean[i]) / m.input_std[i];
    float d = xn - cur[i];
    err += d * d;
  }
  return err / m.in_dim;
}
