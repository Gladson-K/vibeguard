#include "adxl.h"

#include <Arduino.h>
#include <SPI.h>
#include <math.h>

namespace {
int g_cs = -1;
AdxlChip g_chip = ADXL_NONE;

// ADXL345 registers
const uint8_t A345_DEVID = 0x00;
const uint8_t A345_POWER_CTL = 0x2D;
const uint8_t A345_DATA_FORMAT = 0x31;
const uint8_t A345_DATAX0 = 0x32;

// ADXL355 registers
const uint8_t A355_DEVID = 0x00;
const uint8_t A355_RANGE = 0x2C;
const uint8_t A355_POWER_CTL = 0x2D;
const uint8_t A355_XDATA3 = 0x08;

void cs_low() { digitalWrite(g_cs, LOW); }
void cs_high() { digitalWrite(g_cs, HIGH); }

uint8_t rd8(uint8_t reg) {
  cs_low();
  SPI.transfer(reg);
  uint8_t v = SPI.transfer(0x00);
  cs_high();
  return v;
}

void wr8(uint8_t reg, uint8_t val) {
  cs_low();
  SPI.transfer(reg);
  SPI.transfer(val);
  cs_high();
}

uint8_t a355_rd8(uint8_t reg) {  // ADXL355 uses bit0=1 for reads
  cs_low();
  SPI.transfer(reg << 1 | 0x01);
  uint8_t v = SPI.transfer(0x00);
  cs_high();
  return v;
}

void a355_wr8(uint8_t reg, uint8_t val) {
  cs_low();
  SPI.transfer(reg << 1);
  SPI.transfer(val);
  cs_high();
}
}  // namespace

bool adxl_begin(int cs_pin) {
  g_cs = cs_pin;
  pinMode(g_cs, OUTPUT);
  cs_high();
  SPI.begin();

  uint8_t devid = rd8(A345_DEVID);
  if (devid == 0xE5) {
    g_chip = ADXL345;
    wr8(A345_POWER_CTL, 0x00);   // standby
    wr8(A345_DATA_FORMAT, 0x0B); // full res, +-16g
    wr8(A345_POWER_CTL, 0x08);   // measure
    return true;
  }
  uint8_t devid355 = a355_rd8(A355_DEVID);
  if (devid355 == 0xED) {
    g_chip = ADXL355;
    a355_wr8(A355_POWER_CTL, 0x00);
    a355_wr8(A355_RANGE, 0x01);  // +-4g
    a355_wr8(A355_POWER_CTL, 0x00);
    return true;
  }
  g_chip = ADXL_NONE;
  return false;
}

AdxlChip adxl_chip() { return g_chip; }

const char *adxl_chip_name() {
  switch (g_chip) {
    case ADXL345: return "ADXL345";
    case ADXL355: return "ADXL355";
    default: return "none";
  }
}

bool adxl_read_g(float &mag) {
  if (g_chip == ADXL345) {
    cs_low();
    SPI.transfer(A345_DATAX0 | 0x80 | 0x40);  // read + multi-byte
    int16_t ax = (SPI.transfer(0) | (SPI.transfer(0) << 8));
    int16_t ay = (SPI.transfer(0) | (SPI.transfer(0) << 8));
    int16_t az = (SPI.transfer(0) | (SPI.transfer(0) << 8));
    cs_high();
    const float s = 1.0f / 256.0f;  // ~3.9 mg/LSB at full resolution
    mag = sqrtf((ax * s) * (ax * s) + (ay * s) * (ay * s) + (az * s) * (az * s));
    return true;
  }
  if (g_chip == ADXL355) {
    cs_low();
    SPI.transfer(A355_XDATA3 << 1 | 0x01);
    uint8_t x2 = SPI.transfer(0), x1 = SPI.transfer(0), x0 = SPI.transfer(0);
    uint8_t y2 = SPI.transfer(0), y1 = SPI.transfer(0), y0 = SPI.transfer(0);
    uint8_t z2 = SPI.transfer(0), z1 = SPI.transfer(0), z0 = SPI.transfer(0);
    cs_high();
    int32_t ax = (int32_t)((x2 << 12) | (x1 << 4) | (x0 >> 4));
    int32_t ay = (int32_t)((y2 << 12) | (y1 << 4) | (y0 >> 4));
    int32_t az = (int32_t)((z2 << 12) | (z1 << 4) | (z0 >> 4));
    if (ax & 0x80000) ax |= 0xFFF00000;
    if (ay & 0x80000) ay |= 0xFFF00000;
    if (az & 0x80000) az |= 0xFFF00000;
    const float s = 1.0f / 256000.0f;  // +-4g range: 256000 LSB/g
    mag = sqrtf((ax * s) * (ax * s) + (ay * s) * (ay * s) + (az * s) * (az * s));
    return true;
  }
  return false;
}

bool adxl_self_test() {
  // Best-effort WHO_AM_I check used by the production-test jig.
  return g_chip == ADXL345 || g_chip == ADXL355;
}
