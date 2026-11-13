#pragma once
#include <stdint.h>

// Symmetric int8 quantized dense autoencoder runtime (TinyML).
// Weights are int8, activations are int8 per-tensor, accumulation is int32.
enum { VG_ACT_LINEAR = 0, VG_ACT_TANH = 1, VG_ACT_RELU = 2 };

struct QLayer {
  const int8_t *w;  // out_dim * in_dim, row-major
  const float *b;   // out_dim biases (output units)
  float w_scale;
  float in_scale;
  float out_scale;
  int in_dim;
  int out_dim;
  int act;
};

struct QModel {
  const QLayer *layers;
  int n_layers;
  const float *input_mean;
  const float *input_std;
  int in_dim;
  float threshold;
  const char *version;
};

// Returns mean squared reconstruction error in normalized feature space.
float vg_model_score(const QModel &m, const float *feature);
