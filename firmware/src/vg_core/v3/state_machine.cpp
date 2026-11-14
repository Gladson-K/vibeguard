#include "state_machine.h"

namespace vg {

const char *vg_state_name(VgState s) {
  switch (s) {
  case VgState::Boot:
    return "boot";
  case VgState::Provision:
    return "provision";
  case VgState::Sample:
    return "sample";
  case VgState::Infer:
    return "infer";
  case VgState::Tx:
    return "tx";
  case VgState::Ota:
    return "ota";
  case VgState::Sleep:
    return "sleep";
  case VgState::Fault:
    return "fault";
  }
  return "unknown";
}

VgState vg_state_next(VgState cur, const VgStateInputs &in) {
  if (in.fault) return VgState::Fault;
  if (!in.provisioned) return VgState::Provision;

  switch (cur) {
  case VgState::Boot:
  case VgState::Provision:
    return VgState::Sample;
  case VgState::Sample:
    return in.window_ready ? VgState::Infer : VgState::Sample;
  case VgState::Infer:
    return in.ota_requested ? VgState::Ota : VgState::Tx;
  case VgState::Tx:
    if (!in.tx_done) return VgState::Tx;
    return in.ota_requested ? VgState::Ota : VgState::Sleep;
  case VgState::Ota:
    return in.ota_done ? VgState::Sleep : VgState::Ota;
  case VgState::Sleep:
    return in.woke ? VgState::Sample : VgState::Sleep;
  case VgState::Fault:
    return VgState::Boot;
  }
  return VgState::Fault;
}

} // namespace vg
