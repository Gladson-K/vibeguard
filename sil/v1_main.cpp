// V1 software-in-the-loop node: reads raw windows (CSV) on stdin and emits the
// exact firmware feature frames (JSON) on stdout. Shares firmware/src/vg_features_v1.h.
#include <iostream>
#include <string>
#include <vector>

#include "vg_features_v1.h"

static bool parse_args(int argc, char **argv, float &fs, int &n) {
  fs = 1000.0f;
  n = 512;
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
  std::vector<float> buf(n), im(n);
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
    Features f = compute_features(buf.data(), im.data(), n, fs);
    std::cout << "{\"rms\":" << f.rms << ",\"peak\":" << f.peak
              << ",\"crest\":" << f.crest << ",\"kurtosis\":" << f.kurt
              << ",\"dom_freq\":" << f.dom_freq << "}\n";
    std::cout.flush();
  }
  return 0;
}
