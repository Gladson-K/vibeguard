// Host SIL: RUL trend estimate from comma-separated values/times.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "v3_cli.h"
#include "vg_core/v4/rul.h"

static std::vector<float> parse_csv(const char *s) {
  std::vector<float> out;
  if (!s) return out;
  std::string copy(s);
  for (char *tok = std::strtok(&copy[0], ","); tok;
       tok = std::strtok(nullptr, ","))
    out.push_back(float(std::atof(tok)));
  return out;
}

int main(int argc, char **argv) {
  const char *vs = vgcli::arg(argc, argv, "--values");
  std::vector<float> values = parse_csv(vs ? vs : "0.1,0.2,0.3");
  const char *ts = vgcli::arg(argc, argv, "--times");
  std::vector<float> times = parse_csv(ts ? ts : "0,86400,172800");
  float threshold = vgcli::farg(argc, argv, "--threshold", 0.5f);
  if (times.size() < values.size()) times.resize(values.size());
  if (values.size() < times.size()) values.resize(times.size());
  for (size_t i = 0; i < times.size(); i++)
    if (times[i] == 0 && i > 0) times[i] = float(i) * 86400.0f;

  vg::RulEstimate e = vg::rul_estimate(values.data(), times.data(),
                                       values.size(), threshold);
  std::printf("{\"valid\":%s,\"slope_per_day\":%.6f,\"current\":%.4f,"
              "\"rul_days\":%.2f}\n",
              e.valid ? "true" : "false", double(e.slope_per_day),
              double(e.current), double(e.rul_days));
  return 0;
}
