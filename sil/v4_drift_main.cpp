// Host SIL: PSI + KS distribution-shift report.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "v3_cli.h"
#include "vg_core/v4/drift.h"

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
  std::vector<float> ref = parse_csv(vgcli::arg(argc, argv, "--reference"));
  std::vector<float> cur = parse_csv(vgcli::arg(argc, argv, "--current"));
  int bins = int(vgcli::iarg(argc, argv, "--bins", 10));
  float psi_threshold = vgcli::farg(argc, argv, "--psi-threshold", 0.2f);
  float alpha = vgcli::farg(argc, argv, "--alpha", 0.05f);

  vg::DriftReport r = vg::drift_report(ref.data(), ref.size(), cur.data(),
                                       cur.size(), bins, psi_threshold, alpha);
  std::printf("{\"psi\":%.6f,\"ks\":%.6f,\"ks_pvalue\":%.6f,\"drift\":%s}\n",
              double(r.psi), double(r.ks), double(r.ks_pvalue),
              r.drift ? "true" : "false");
  return 0;
}
