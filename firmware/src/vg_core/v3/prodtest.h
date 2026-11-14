#pragma once

// Production-test-jig policy: turn raw board measurements into a pass/fail and
// a printable label. Portable so the pogo-pin station and CI share the rules.
namespace vg {

struct BoardChecks {
  bool rail_3v3 = false;
  bool rail_1v8 = false;
  bool flash_ok = false;
  bool whoami = false;
  bool selftest = false;
  const char *sensor = "adxl355";
  const char *firmware = "3.0.0";
};

struct ProdTestResult {
  bool pass;
  char reason[32];
  char label[128];
};

ProdTestResult prodtest_evaluate(const BoardChecks &c, const char *device_id);

} // namespace vg
