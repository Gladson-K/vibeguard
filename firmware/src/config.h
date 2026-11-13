#pragma once
#define WIFI_SSID     "your-wifi"
#define WIFI_PASS     "your-pass"
#define GATEWAY_HOST  "192.168.1.50"   // gateway IP
#define GATEWAY_PORT  8000
#define DEVICE_ID     "node-01"
#define USE_MQTT      0                // 1 = publish via MQTT instead of HTTP
#define MQTT_PORT     1883

// --- V1 sensing (MPU-6050 over I2C) ---
#define FS_HZ         1000
#define WINDOW_N      512              // power of two
#define PIN_SDA       8
#define PIN_SCL       9

// --- V2 sensing (ADXL345/ADXL355 over SPI) ---
#define FS_HZ_V2      3200
#define WINDOW_N_V2   2048             // power of two
#define PIN_ADXL_CS   10
#define ADXL_SPI_HZ   4000000
