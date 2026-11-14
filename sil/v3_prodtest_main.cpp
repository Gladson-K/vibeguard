// Host SIL: run the production-test-jig policy on a measured board.
#include <cstdio>

#include "vg_core/v3/prodtest.h"
#include "v3_cli.h"

int main(int argc, char **argv) {
  vg::BoardChecks c;
  c.rail_3v3 = vgcli::barg(argc, argv, "--rail-3v3", false);
  c.rail_1v8 = vgcli::barg(argc, argv, "--rail-1v8", false);
  c.flash_ok = vgcli::barg(argc, argv, "--flash", false);
  c.whoami = vgcli::barg(argc, argv, "--whoami", false);
  c.selftest = vgcli::barg(argc, argv, "--selftest", false);
  c.sensor = vgcli::arg(argc, argv, "--sensor");
  if (!c.sensor) c.sensor = "adxl355";
  c.firmware = vgcli::arg(argc, argv, "--firmware");
  if (!c.firmware) c.firmware = "3.0.0";
  const char *id = vgcli::arg(argc, argv, "--device-id");
  if (!id) id = "unknown";

  vg::ProdTestResult r = vg::prodtest_evaluate(c, id);
  std::printf("{\"pass\":%s,\"reason\":\"%s\",\"label\":\"%s\"}\n",
              r.pass ? "true" : "false", r.reason, r.label);
  return r.pass ? 0 : 1;
}
