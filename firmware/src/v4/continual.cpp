#include "continual.h"

#include <string.h>

void continual_begin(ContinualState *s) {
  if (!s) return;
  memset(s, 0, sizeof(*s));
}

void continual_refresh(ContinualState *s) {
  if (!s) return;
  int n = s->recent_n < VG_DRIFT_WINDOW ? s->recent_n : VG_DRIFT_WINDOW;
  for (int i = 0; i < n; i++) s->reference[i] = s->recent[i];
  s->ref_n = n;
  s->head = 0;
  s->recent_n = 0;
  s->since_check = 0;
  s->drift = false;
  s->last_psi = 0;
  s->last_ks = 0;
}

bool continual_update(ContinualState *s, float value) {
  if (!s) return false;
  if (s->ref_n < VG_DRIFT_WINDOW) {
    s->reference[s->ref_n++] = value;
    return false;
  }
  s->recent[s->head] = value;
  s->head = (s->head + 1) % VG_DRIFT_WINDOW;
  if (s->recent_n < VG_DRIFT_WINDOW) s->recent_n++;
  s->since_check++;
  if (s->since_check < VG_DRIFT_INTERVAL || s->recent_n < VG_DRIFT_WINDOW)
    return false;
  s->since_check = 0;
  vg::DriftReport rep = continual_report(s);
  s->last_psi = rep.psi;
  s->last_ks = rep.ks;
  s->drift = rep.drift;
  return rep.drift;
}

vg::DriftReport continual_report(const ContinualState *s) {
  if (!s || s->ref_n == 0 || s->recent_n == 0) return vg::DriftReport();
  return vg::drift_report(s->reference, size_t(s->ref_n), s->recent,
                          size_t(s->recent_n), 10, VG_DRIFT_PSI_THRESHOLD,
                          VG_DRIFT_ALPHA);
}
