#pragma once
#include <stdint.h>

// Deterministic staged-rollout policy shared by gateway and device. Bucketing
// uses FNV-1a so the same device stays in the same 10% cohort across reboots
// and across server restarts.
namespace vg {

uint32_t fnv1a32(const char *s);
int rollout_bucket(const char *device_id);          // 0..99
bool rollout_selected(const char *device_id, int percent);
int rollout_stage_percent(int stage);               // stage 0 => 10, 1 => 50, 2 => 100

} // namespace vg
