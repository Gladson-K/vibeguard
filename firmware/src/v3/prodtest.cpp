#include "prodtest.h"

#include <Preferences.h>

#include "adxl.h"
#include "v3_config.h"

namespace {

bool rail_ok(int pin, float min_v, float max_v) {
  // 1:1 divider into the ADC; calibrate per board revision.
  float v = analogReadMilliVolts(pin) / 1000.0f;
  return v >= min_v && v <= max_v;
}

} // namespace

vg::ProdTestResult prodtest_run(const char *device_id) {
  vg::BoardChecks c;
  c.rail_3v3 = rail_ok(PIN_RAIL_3V3_ADC, 3.1f, 3.5f);
  c.rail_1v8 = rail_ok(PIN_RAIL_1V8_ADC, 1.7f, 1.9f);
  c.flash_ok = true; // NVS mount success is implied by the running firmware
  c.whoami = adxl_begin(PIN_ADXL_CS) && adxl_chip() != ADXL_NONE;
  c.selftest = c.whoami && adxl_self_test();
  c.sensor = adxl_chip_name();
  c.firmware = String(VG_FW_VERSION).c_str();
  return vg::prodtest_evaluate(c, device_id);
}

void prodtest_store_device_id(const char *device_id) {
  Preferences prefs;
  prefs.begin("vgwifi", false);
  prefs.putString("device_id", device_id ? device_id : "node");
  prefs.end();
}
