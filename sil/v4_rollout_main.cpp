// Host SIL: deterministic staged-rollout bucket for a device id.
#include <cstdio>

#include "v3_cli.h"
#include "vg_core/v4/rollout.h"

int main(int argc, char **argv) {
  const char *id = vgcli::arg(argc, argv, "--device-id");
  if (!id) id = "bench-01";
  int percent = int(vgcli::iarg(argc, argv, "--percent", -1));
  if (percent < 0) {
    int stage = int(vgcli::iarg(argc, argv, "--stage", 0));
    percent = vg::rollout_stage_percent(stage);
  }
  int bucket = vg::rollout_bucket(id);
  bool selected = vg::rollout_selected(id, percent);
  std::printf("{\"device_id\":\"%s\",\"bucket\":%d,\"percent\":%d,"
              "\"selected\":%s}\n",
              id, bucket, percent, selected ? "true" : "false");
  return 0;
}
