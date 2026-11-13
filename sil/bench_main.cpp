// Device-side inference benchmark for the int8 TinyML model.
#include <chrono>
#include <cstdio>
#include <string>

#include "vg_core/model.h"
#include "vg_core/model_data.h"

int main(int argc, char **argv) {
  int iters = 20000;
  for (int i = 1; i < argc; i++) {
    std::string a = argv[i];
    if (a == "--iters" && i + 1 < argc) iters = std::stoi(argv[++i]);
  }
  float feat[VG_MODEL_IN_DIM];
  for (int i = 0; i < VG_MODEL_IN_DIM; i++) feat[i] = 0.01f * (float)(i % 7);
  volatile float sink = 0;
  sink += vg_model_score(VG_MODEL, feat);  // warm up
  auto t0 = std::chrono::steady_clock::now();
  for (int i = 0; i < iters; i++) sink += vg_model_score(VG_MODEL, feat);
  auto t1 = std::chrono::steady_clock::now();
  double us = std::chrono::duration<double, std::micro>(t1 - t0).count() / iters;
  std::printf("{\"us_per_infer\":%.3f,\"iters\":%d}\n", us, iters);
  return 0;
}
