#include "power.h"

#include <esp_sleep.h>

RTC_DATA_ATTR static uint32_t s_boot_count = 0;

void power_begin() {
  s_boot_count++;
  esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  Serial.printf("boot=%u wake=%d\n", s_boot_count, int(cause));
}

uint32_t power_boot_count() { return s_boot_count; }

void power_deep_sleep(uint32_t seconds) {
  if (seconds == 0) seconds = 1;
  esp_sleep_enable_timer_wakeup(uint64_t(seconds) * 1000000ULL);
  Serial.flush();
  esp_deep_sleep_start();
}
