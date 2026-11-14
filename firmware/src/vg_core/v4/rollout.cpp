#include "rollout.h"

namespace vg {

uint32_t fnv1a32(const char *s) {
  uint32_t h = 2166136261u;
  if (!s) return h;
  for (const unsigned char *p = reinterpret_cast<const unsigned char *>(s); *p;
       p++) {
    h ^= *p;
    h *= 16777619u;
  }
  return h;
}

int rollout_bucket(const char *device_id) {
  return int(fnv1a32(device_id) % 100u);
}

bool rollout_selected(const char *device_id, int percent) {
  if (percent >= 100) return true;
  if (percent <= 0) return false;
  return rollout_bucket(device_id) < percent;
}

int rollout_stage_percent(int stage) {
  switch (stage) {
  case 0:
    return 10;
  case 1:
    return 50;
  default:
    return 100;
  }
}

} // namespace vg
