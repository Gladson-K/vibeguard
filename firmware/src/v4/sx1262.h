#pragma once
#include <Arduino.h>
#include <SPI.h>

// Minimal SX1262 LoRa transceiver driver (SPI, blocking command mode). It
// exposes just what the fleet node and the Pi/ESP gateway bridge need: packet
// TX, packet RX with timeout, RSSI and IRQ handling.
class Sx1262 {
 public:
  bool begin(SPIClass &spi, int sck, int miso, int mosi, int cs, int reset,
             int busy, int dio1);
  bool configure(float freq_mhz, int sf, float bw_khz, int cr, int preamble,
                 int tx_dbm, uint16_t sync_word);
  bool transmit(const uint8_t *data, size_t len);
  int receive(uint8_t *out, size_t cap, uint32_t timeout_ms);
  int16_t packet_rssi() const { return rssi_; }
  bool ready() const { return ready_; }

 private:
  void reset();
  void wait_busy();
  void command(uint8_t opcode, const uint8_t *args, size_t len);
  void write_buffer(uint8_t offset, const uint8_t *data, size_t len);
  void read_buffer(uint8_t offset, uint8_t *data, size_t len);
  uint16_t irq_status();
  void clear_irq(uint16_t mask);

  SPIClass *spi_ = nullptr;
  int cs_ = -1, reset_ = -1, busy_ = -1, dio1_ = -1;
  int16_t rssi_ = 0;
  bool ready_ = false;
};
