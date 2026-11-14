#pragma once
#include <stdint.h>

#include "v4_config.h"
#include "vg_core/v4/drift.h"

// On-device continual-learning shadow: keeps a frozen reference window and a
// recent window, evaluates PSI/KS every VG_DRIFT_INTERVAL samples and raises a
// drift flag for telemetry. Baseline refresh only happens after an operator
// approval (or a locally confirmed maintenance window).
struct ContinualState {
  float reference[VG_DRIFT_WINDOW];
  float recent[VG_DRIFT_WINDOW];
  int ref_n;
  int recent_n;
  int head;
  int since_check;
  float last_psi;
  float last_ks;
  bool drift;
};

void continual_begin(ContinualState *s);
bool continual_update(ContinualState *s, float value);
void continual_refresh(ContinualState *s);
vg::DriftReport continual_report(const ContinualState *s);
