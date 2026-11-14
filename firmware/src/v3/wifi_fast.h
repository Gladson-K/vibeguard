#pragma once
#include <Arduino.h>

// Fast Wi-Fi reconnect using the stored BSSID/channel/static IP. The first
// association after provisioning is a normal scan; later boots skip scanning.
bool wifi_fast_connect(uint32_t timeout_ms);
bool wifi_fast_connected();
void wifi_fast_store(); // call after a successful association

// Credentials are written by the SoftAP provisioning flow.
bool wifi_credentials_saved();
