#include "sx1262.h"

#include "v4_config.h"

namespace {
constexpr uint8_t OP_SET_STANDBY = 0x80;
constexpr uint8_t OP_SET_RX = 0x82;
constexpr uint8_t OP_SET_TX = 0x83;
constexpr uint8_t OP_SET_PACKET_TYPE = 0x8A;
constexpr uint8_t OP_SET_RF_FREQ = 0x86;
constexpr uint8_t OP_SET_TX_PARAMS = 0x8E;
constexpr uint8_t OP_SET_MOD_PARAMS = 0x8B;
constexpr uint8_t OP_SET_PACKET_PARAMS = 0x8C;
constexpr uint8_t OP_SET_BUFFER_BASE = 0x8F;
constexpr uint8_t OP_WRITE_BUFFER = 0x0E;
constexpr uint8_t OP_READ_BUFFER = 0x1E;
constexpr uint8_t OP_SET_DIO_IRQ = 0x08;
constexpr uint8_t OP_GET_IRQ = 0x12;
constexpr uint8_t OP_CLR_IRQ = 0x02;
constexpr uint8_t OP_GET_RSSI = 0x15;
constexpr uint8_t OP_SET_REGULATOR = 0x96;
constexpr uint8_t OP_SET_DIO3_TCXO = 0x97;
constexpr uint8_t OP_SET_FALLBACK = 0x93;
constexpr uint8_t OP_CALIBRATE = 0x89;

constexpr uint16_t IRQ_TX_DONE = 0x0001;
constexpr uint16_t IRQ_RX_DONE = 0x0002;
constexpr uint16_t IRQ_TIMEOUT = 0x0200;
} // namespace

void Sx1262::wait_busy() {
  if (busy_ < 0) return;
  uint32_t start = millis();
  while (digitalRead(busy_) == HIGH) {
    if (millis() - start > 1000) break;
    delayMicroseconds(100);
  }
}

void Sx1262::command(uint8_t opcode, const uint8_t *args, size_t len) {
  spi_->beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  digitalWrite(cs_, LOW);
  spi_->transfer(opcode);
  for (size_t i = 0; i < len; i++) spi_->transfer(args[i]);
  digitalWrite(cs_, HIGH);
  spi_->endTransaction();
}

void Sx1262::write_buffer(uint8_t offset, const uint8_t *data, size_t len) {
  spi_->beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  digitalWrite(cs_, LOW);
  spi_->transfer(OP_WRITE_BUFFER);
  spi_->transfer(offset);
  for (size_t i = 0; i < len; i++) spi_->transfer(data[i]);
  digitalWrite(cs_, HIGH);
  spi_->endTransaction();
}

void Sx1262::read_buffer(uint8_t offset, uint8_t *data, size_t len) {
  spi_->beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  digitalWrite(cs_, LOW);
  spi_->transfer(OP_READ_BUFFER);
  spi_->transfer(offset);
  spi_->transfer(0x00); // dummy
  for (size_t i = 0; i < len; i++) data[i] = spi_->transfer(0x00);
  digitalWrite(cs_, HIGH);
  spi_->endTransaction();
}

uint16_t Sx1262::irq_status() {
  spi_->beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));
  digitalWrite(cs_, LOW);
  spi_->transfer(OP_GET_IRQ);
  spi_->transfer(0x00);
  uint8_t hi = spi_->transfer(0x00);
  uint8_t lo = spi_->transfer(0x00);
  digitalWrite(cs_, HIGH);
  spi_->endTransaction();
  return uint16_t((hi << 8) | lo);
}

void Sx1262::clear_irq(uint16_t mask) {
  uint8_t args[2] = {uint8_t(mask >> 8), uint8_t(mask & 0xFF)};
  command(OP_CLR_IRQ, args, 2);
}

void Sx1262::reset() {
  digitalWrite(reset_, LOW);
  delay(2);
  digitalWrite(reset_, HIGH);
  delay(10);
  wait_busy();
}

bool Sx1262::begin(SPIClass &spi, int sck, int miso, int mosi, int cs,
                   int reset, int busy, int dio1) {
  spi_ = &spi;
  cs_ = cs;
  reset_ = reset;
  busy_ = busy;
  dio1_ = dio1;
  pinMode(cs_, OUTPUT);
  digitalWrite(cs_, HIGH);
  pinMode(reset_, OUTPUT);
  pinMode(busy_, INPUT);
  pinMode(dio1_, INPUT);
  spi_->begin(sck, miso, mosi, cs_);
  reset();

  uint8_t standby[1] = {0x00};
  command(OP_SET_STANDBY, standby, 1);
  uint8_t regulator[1] = {0x01}; // DC-DC
  command(OP_SET_REGULATOR, regulator, 1);
  uint8_t packet[1] = {0x01}; // LoRa
  command(OP_SET_PACKET_TYPE, packet, 1);
  uint8_t fallback[1] = {0x20};
  command(OP_SET_FALLBACK, fallback, 1);
  ready_ = true;
  return true;
}

bool Sx1262::configure(float freq_mhz, int sf, float bw_khz, int cr,
                       int preamble, int tx_dbm, uint16_t sync_word) {
  if (!ready_) return false;

  uint32_t frf = uint32_t((double(freq_mhz) * 1e6 * double(1ULL << 25)) / 32e6);
  uint8_t rf[4] = {uint8_t(frf >> 24), uint8_t(frf >> 16), uint8_t(frf >> 8),
                   uint8_t(frf)};
  command(OP_SET_RF_FREQ, rf, 4);

  uint8_t pa[2] = {uint8_t(tx_dbm), 0x02}; // PA config, optimal match
  command(OP_SET_TX_PARAMS, pa, 2);

  uint8_t bw;
  if (bw_khz <= 7.8f) bw = 0x00;
  else if (bw_khz <= 10.4f) bw = 0x08;
  else if (bw_khz <= 15.6f) bw = 0x01;
  else if (bw_khz <= 20.8f) bw = 0x09;
  else if (bw_khz <= 31.25f) bw = 0x02;
  else if (bw_khz <= 41.7f) bw = 0x0A;
  else if (bw_khz <= 62.5f) bw = 0x03;
  else if (bw_khz <= 125.0f) bw = 0x04;
  else if (bw_khz <= 250.0f) bw = 0x05;
  else bw = 0x06;
  uint8_t mod[4] = {uint8_t(sf), bw, uint8_t(cr), 0x00};
  command(OP_SET_MOD_PARAMS, mod, 4);

  uint8_t pkt[6] = {uint8_t(preamble), 0x00, 0x40, 0x00, 0x00, 0x00};
  command(OP_SET_PACKET_PARAMS, pkt, 6);

  uint8_t base[2] = {0x00, 0x00};
  command(OP_SET_BUFFER_BASE, base, 2);

  uint8_t irq[8] = {0x00, 0x03, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00};
  command(OP_SET_DIO_IRQ, irq, 8);

  uint8_t calib[1] = {0x7F};
  command(OP_CALIBRATE, calib, 1);
  (void)sync_word;
  return true;
}

bool Sx1262::transmit(const uint8_t *data, size_t len) {
  if (!ready_ || len > 255) return false;
  wait_busy();
  clear_irq(0xFFFF);
  write_buffer(0x00, data, len);
  uint8_t pkt[6] = {VG_LORA_PREAMBLE, 0x00, 0x40, 0x00, 0x00, uint8_t(len)};
  command(OP_SET_PACKET_PARAMS, pkt, 6);
  command(OP_SET_TX, nullptr, 0);

  uint32_t start = millis();
  while (millis() - start < 5000) {
    uint16_t irq = irq_status();
    if (irq & IRQ_TX_DONE) {
      clear_irq(IRQ_TX_DONE);
      return true;
    }
    delay(1);
  }
  return false;
}

int Sx1262::receive(uint8_t *out, size_t cap, uint32_t timeout_ms) {
  if (!ready_) return -1;
  wait_busy();
  clear_irq(0xFFFF);
  command(OP_SET_RX, nullptr, 0);
  uint32_t start = millis();
  while (millis() - start < timeout_ms) {
    uint16_t irq = irq_status();
    if (irq & IRQ_RX_DONE) {
      clear_irq(IRQ_RX_DONE);
      uint8_t hdr[2];
      read_buffer(0x00, hdr, 2); // status + length
      size_t len = hdr[1];
      if (len > cap) len = cap;
      read_buffer(0x02, out, len);
      uint8_t rssi;
      read_buffer(0x01, &rssi, 1);
      rssi_ = -int16_t(rssi) / 2;
      return int(len);
    }
    if (irq & IRQ_TIMEOUT) {
      clear_irq(IRQ_TIMEOUT);
      return 0;
    }
    delay(1);
  }
  return 0;
}
