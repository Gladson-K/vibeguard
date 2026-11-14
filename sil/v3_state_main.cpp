// Host SIL: evaluate one transition of the V3 deep-sleep state machine.
#include <cstdio>
#include <cstring>

#include "vg_core/v3/state_machine.h"
#include "v3_cli.h"

static vg::VgState parse_state(const char *s) {
  const vg::VgState all[] = {vg::VgState::Boot,      vg::VgState::Provision,
                             vg::VgState::Sample,    vg::VgState::Infer,
                             vg::VgState::Tx,        vg::VgState::Ota,
                             vg::VgState::Sleep,     vg::VgState::Fault};
  for (vg::VgState st : all)
    if (std::strcmp(vg::vg_state_name(st), s) == 0) return st;
  return vg::VgState::Fault;
}

int main(int argc, char **argv) {
  const char *name = vgcli::arg(argc, argv, "--state");
  vg::VgState cur = parse_state(name ? name : "boot");

  vg::VgStateInputs in;
  in.provisioned = vgcli::barg(argc, argv, "--provisioned", true);
  in.window_ready = vgcli::barg(argc, argv, "--window-ready", false);
  in.tx_done = vgcli::barg(argc, argv, "--tx-done", false);
  in.ota_requested = vgcli::barg(argc, argv, "--ota-requested", false);
  in.ota_done = vgcli::barg(argc, argv, "--ota-done", false);
  in.fault = vgcli::barg(argc, argv, "--fault", false);
  in.woke = vgcli::barg(argc, argv, "--woke", true);

  vg::VgState next = vg::vg_state_next(cur, in);
  std::printf("{\"state\":\"%s\"}\n", vg::vg_state_name(next));
  return 0;
}
