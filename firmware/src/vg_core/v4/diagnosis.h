#pragma once

// Bearing-defect frequencies + rule-based fault diagnosis (V4 deliverable 4).
// Order tracking/envelope analysis produces `envelope_freq`; this module maps
// geometry and features to a first-pass class. The gateway mirrors it in
// gateway/diagnosis.py.
namespace vg {

struct BearingGeometry {
  float rpm = 0;
  int n_balls = 0;
  float ball_d_mm = 0;
  float pitch_d_mm = 0;
  float contact_angle_deg = 0;
};

struct BearingFreqs {
  float bpfo = 0;
  float bpfi = 0;
  float bsf = 0;
  float ftf = 0;
  bool valid = false;
};

struct DiagnosisInput {
  float rms = 0;
  float crest = 0;
  float kurtosis = 0;
  float dom_freq = 0;
  float envelope_freq = 0; // 0 = not available
};

enum class FaultClass {
  Unknown = 0,
  Imbalance,
  Misalignment,
  Looseness,
  Bearing,
};

const char *fault_name(FaultClass c);
BearingFreqs bearing_frequencies(const BearingGeometry &g);
FaultClass diagnose(const DiagnosisInput &in, const BearingFreqs &f,
                    float tol_hz = 5.0f);

} // namespace vg
