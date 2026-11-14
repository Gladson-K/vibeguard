// Host SIL: bearing frequencies + rule-based diagnosis.
#include <cstdio>

#include "v3_cli.h"
#include "vg_core/v4/diagnosis.h"

int main(int argc, char **argv) {
  vg::BearingGeometry g;
  g.rpm = vgcli::farg(argc, argv, "--rpm", 1500.0f);
  g.n_balls = int(vgcli::iarg(argc, argv, "--n-balls", 8));
  g.ball_d_mm = vgcli::farg(argc, argv, "--ball-d", 7.94f);
  g.pitch_d_mm = vgcli::farg(argc, argv, "--pitch-d", 39.04f);
  g.contact_angle_deg = vgcli::farg(argc, argv, "--contact-angle", 0.0f);

  vg::BearingFreqs f = vg::bearing_frequencies(g);

  vg::DiagnosisInput in;
  in.rms = vgcli::farg(argc, argv, "--rms", 0.1f);
  in.crest = vgcli::farg(argc, argv, "--crest", 3.0f);
  in.kurtosis = vgcli::farg(argc, argv, "--kurtosis", 2.9f);
  in.dom_freq = vgcli::farg(argc, argv, "--dom-freq", 0.0f);
  in.envelope_freq = vgcli::farg(argc, argv, "--envelope-freq", 0.0f);

  vg::FaultClass c = vg::diagnose(in, f);
  std::printf("{\"valid\":%s,\"bpfo\":%.2f,\"bpfi\":%.2f,\"bsf\":%.2f,"
              "\"ftf\":%.3f,\"class\":\"%s\"}\n",
              f.valid ? "true" : "false", double(f.bpfo), double(f.bpfi),
              double(f.bsf), double(f.ftf), vg::fault_name(c));
  return 0;
}
