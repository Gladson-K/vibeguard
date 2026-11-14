#include "prodtest.h"

#include <cstdio>
#include <cstring>

namespace vg {
namespace {
const char *first_failure(const BoardChecks &c) {
  if (!c.rail_3v3) return "rail_3v3";
  if (!c.rail_1v8) return "rail_1v8";
  if (!c.flash_ok) return "flash";
  if (!c.whoami) return "whoami";
  if (!c.selftest) return "selftest";
  return nullptr;
}
} // namespace

ProdTestResult prodtest_evaluate(const BoardChecks &c, const char *device_id) {
  ProdTestResult r{};
  const char *fail = first_failure(c);
  r.pass = fail == nullptr;
  std::snprintf(r.reason, sizeof(r.reason), "%s", r.pass ? "ok" : fail);
  std::snprintf(r.label, sizeof(r.label), "VG3-%s-%s-%s-%s%s",
                device_id ? device_id : "unknown",
                c.sensor ? c.sensor : "unknown",
                c.firmware ? c.firmware : "unknown",
                r.pass ? "PASS" : "FAIL-", r.pass ? "" : fail);
  return r;
}

} // namespace vg
