#pragma once
#include <stdint.h>

// SPI accelerometer driver supporting ADXL345 and ADXL355 (V2 sensing upgrade).
enum AdxlChip { ADXL_NONE = 0, ADXL345 = 1, ADXL355 = 2 };

bool adxl_begin(int cs_pin);
AdxlChip adxl_chip();
const char *adxl_chip_name();
bool adxl_read_g(float &mag);
bool adxl_self_test();
