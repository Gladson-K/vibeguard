// V2 software-in-the-loop node: raw windows in, V2 features + int8 TinyML score out.
#include <iostream>
#include <string>
#include <vector>

#include "vg_core/features_v2.h"
#include "vg_core/model.h"
#include "vg_core/model_data.h"

static bool parse_args(int argc, char **argv, float &fs, int &n) {
  fs = 3200.0f;
  n = 2048;
  for (int i = 1; i < argc; i++) {
    std::string arg = argv[i];
    if (arg == "--fs" && i + 1 < argc) fs = std::stof(argv[++i]);
    else if (arg == "--n" && i + 1 < argc) n = std::stoi(argv[++i]);
  }
  return n >= 8 && (n & (n - 1)) == 0;
}

int main(int argc, char **argv) {
  std::cout.precision(9);
  float fs;
  int n;
  if (!parse_args(argc, argv, fs, n)) {
    std::cerr << "usage: " << argv[0] << " [--fs HZ] [--n POWER_OF_TWO]\n";
    return 2;
  }
  std::vector<float> buf(n);
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty()) continue;
    int count = 0;
    std::string::size_type pos = 0;
    while (pos < line.size() && count < n) {
      std::string::size_type comma = line.find(',', pos);
      if (comma == std::string::npos) comma = line.size();
      buf[count++] = std::stof(line.substr(pos, comma - pos));
      pos = comma + 1;
    }
    if (count != n) {
      std::cerr << "expected " << n << " samples, got " << count << "\n";
      return 3;
    }
    V2Features f;
    vg_compute_features_v2(buf.data(), n, fs, &f);
    float score = vg_model_score(VG_MODEL, f.vector);
    std::cout << "{\"rms\":" << f.rms << ",\"peak\":" << f.peak
              << ",\"crest\":" << f.crest << ",\"kurtosis\":" << f.kurtosis
              << ",\"dom_freq\":" << f.dom_freq << ",\"centroid\":" << f.centroid
              << ",\"bands\":[";
    for (int b = 0; b < VG_V2_BANDS; b++) {
      if (b) std::cout << ",";
      std::cout << f.bands[b];
    }
    std::cout << "],\"model_score\":" << score
              << ",\"model_version\":\"" << VG_MODEL.version << "\"}\n";
    std::cout.flush();
  }
  return 0;
}
