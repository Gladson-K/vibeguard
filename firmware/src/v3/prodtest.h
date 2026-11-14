#pragma once
#include <Arduino.h>

#include "vg_core/v3/prodtest.h"

// Runs the pogo-pin station checks (rails, flash, WHO_AM_I, self-test) and
// returns the shared pass/fail + printable label.
vg::ProdTestResult prodtest_run(const char *device_id);
void prodtest_store_device_id(const char *device_id);
