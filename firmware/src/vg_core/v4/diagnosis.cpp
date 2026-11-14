#include "diagnosis.h"

#include <cmath>

namespace vg {
namespace {

bool near(float value, float target, float tol) {
  return target > 0.0f && std::fabs(value - target) <= tol;
}

} // namespace

const char *fault_name(FaultClass c) {
  switch (c) {
  case FaultClass::Unknown:
    return "unknown";
  case FaultClass::Imbalance:
    return "imbalance";
  case FaultClass::Misalignment:
    return "misalignment";
  case FaultClass::Looseness:
    return "looseness";
  case FaultClass::Bearing:
    return "bearing";
  }
  return "unknown";
}

BearingFreqs bearing_frequencies(const BearingGeometry &g) {
  BearingFreqs f;
  if (g.rpm <= 0.0f || g.n_balls <= 0 || g.ball_d_mm <= 0.0f ||
      g.pitch_d_mm <= 0.0f || g.pitch_d_mm <= g.ball_d_mm)
    return f;

  const float fr = g.rpm / 60.0f;
  const float ratio = (g.ball_d_mm / g.pitch_d_mm) *
                      std::cos(g.contact_angle_deg * 3.14159265358979323846f /
                               180.0f);
  f.bpfo = (g.n_balls / 2.0f) * fr * (1.0f - ratio);
  f.bpfi = (g.n_balls / 2.0f) * fr * (1.0f + ratio);
  f.bsf = (g.pitch_d_mm / (2.0f * g.ball_d_mm)) * fr * (1.0f - ratio * ratio);
  f.ftf = (fr / 2.0f) * (1.0f - ratio);
  f.valid = true;
  return f;
}

FaultClass diagnose(const DiagnosisInput &in, const BearingFreqs &f,
                    float tol_hz) {
  if (in.kurtosis >= 4.0f && in.envelope_freq > 0.0f && f.valid) {
    if (near(in.envelope_freq, f.bpfo, tol_hz * 2) ||
        near(in.envelope_freq, f.bpfi, tol_hz * 2) ||
        near(in.envelope_freq, f.bsf, tol_hz * 2) ||
        near(in.envelope_freq, f.ftf, tol_hz * 2))
      return FaultClass::Bearing;
  }

  if (in.kurtosis >= 5.0f && f.valid) {
    if (near(in.dom_freq, f.bpfo, tol_hz * 2) ||
        near(in.dom_freq, f.bpfi, tol_hz * 2) ||
        near(in.dom_freq, f.bsf, tol_hz * 2) ||
        near(in.dom_freq, f.ftf, tol_hz * 2))
      return FaultClass::Bearing;
  }

  const float one_x = f.valid ? f.ftf * 2.0f : 0.0f;
  if (one_x > 0.0f && near(in.dom_freq, 2.0f * one_x, tol_hz * 2))
    return FaultClass::Misalignment;
  if (one_x > 0.0f && near(in.dom_freq, one_x, tol_hz * 2) &&
      in.kurtosis < 4.5f)
    return FaultClass::Imbalance;
  if (in.crest >= 5.0f || in.kurtosis >= 6.0f) return FaultClass::Looseness;
  return FaultClass::Unknown;
}

} // namespace vg
