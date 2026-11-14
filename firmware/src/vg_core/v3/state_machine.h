#pragma once

#include <stdint.h>

// V3 deep-sleep duty-cycle state machine. Pure logic so wake/sleep decisions
// can be tested on the host, while firmware/src/v3/power.cpp only provides the
// ESP32 sleep call.
namespace vg {

enum class VgState {
  Boot = 0,
  Provision,
  Sample,
  Infer,
  Tx,
  Ota,
  Sleep,
  Fault,
};

struct VgStateInputs {
  bool provisioned = true;
  bool window_ready = false;
  bool tx_done = false;
  bool ota_requested = false;
  bool ota_done = false;
  bool fault = false;
  bool woke = true;
};

const char *vg_state_name(VgState s);
VgState vg_state_next(VgState cur, const VgStateInputs &in);

} // namespace vg
